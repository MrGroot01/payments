# FILE: payments/views.py

import hmac
import hashlib
import json
import logging

import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem
from .serializers import CreateOrderSerializer, OrderSerializer, VerifyPaymentSerializer

logger = logging.getLogger(__name__)

# Razorpay client
rzp_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# ───────────────────────────────────────────────
# CREATE ORDER
# ───────────────────────────────────────────────
class CreateOrderView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = CreateOrderSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data

        subtotal = sum(
            float(item["price"]) * int(item.get("quantity", item.get("qyt", 1)))
            for item in data["items"]
        )
        total = subtotal + float(data["delivery_charge"])
        amount_paise = int(total * 100)

        try:
            rzp_order = rzp_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"receipt_{int(amount_paise)}",
                "payment_capture": 1,
            })
        except Exception as exc:
            logger.error("Razorpay error: %s", exc)
            return Response({"detail": "Payment error"}, status=500)

        # ✅ FIX: handle user safely
        user = request.user if request.user.is_authenticated else None

        order = Order.objects.create(
            user=user,   # ✅ IMPORTANT FIX
            amount=total,
            currency="INR",
            status="PENDING",
            razorpay_order_id=rzp_order["id"],
            delivery_address=data["delivery_address"],
            delivery_charge=data["delivery_charge"],
        )

        for item in data["items"]:
            OrderItem.objects.create(
                order=order,
                product_id=str(item.get("id", "")),
                name=item.get("name", ""),
                price=float(item.get("price", 0)),
                quantity=int(item.get("quantity", item.get("qyt", 1))),
            )

        return Response({
            "order_id": str(order.id),   # ✅ better for frontend
            "razorpay_order_id": rzp_order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "key": settings.RAZORPAY_KEY_ID,
        })


# ───────────────────────────────────────────────
# VERIFY PAYMENT
# ───────────────────────────────────────────────
class VerifyPaymentView(APIView):
    permission_classes = [AllowAny]   # ✅ FIXED

    def post(self, request):
        ser = VerifyPaymentSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)

        d = ser.validated_data

        try:
            order = Order.objects.get(
                razorpay_order_id=d["razorpay_order_id"]
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)

        payload = f"{d['razorpay_order_id']}|{d['razorpay_payment_id']}"
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, d["razorpay_signature"]):
            order.status = "FAILED"
            order.save()
            return Response({"detail": "Verification failed"}, status=400)

        order.status = "SUCCESS"
        order.razorpay_payment_id = d["razorpay_payment_id"]
        order.save()

        return Response({"detail": "Payment success"})


# ───────────────────────────────────────────────
# ORDER STATUS
# ───────────────────────────────────────────────
class OrderStatusView(APIView):
    permission_classes = [AllowAny]   # ✅ FIXED

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        return Response({
            "id": order.id,
            "status": order.status
        })


# ───────────────────────────────────────────────
# WEBHOOK (optional)
# ───────────────────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({"status": "ok"})