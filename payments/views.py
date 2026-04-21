import hmac
import hashlib
import logging

import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────
# 🔥 CREATE RAZORPAY CLIENT SAFELY (FIXED)
# ───────────────────────────────────────────────
def get_razorpay_client():
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET

    print("🔑 KEY ID:", key_id)
    print("🔑 KEY SECRET:", key_secret)

    if not key_id or not key_secret:
        raise Exception("Razorpay keys not configured")

    return razorpay.Client(auth=(key_id, key_secret))


# ───────────────────────────────────────────────
# CREATE ORDER
# ───────────────────────────────────────────────
class CreateOrderView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        try:
            items = data.get("items", [])
            delivery_charge = float(data.get("delivery_charge", 0))
            delivery_address = data.get("delivery_address", "")

            latitude = data.get("latitude")
            longitude = data.get("longitude")

            if not items:
                return Response({"error": "Cart is empty"}, status=400)

            subtotal = sum(
                float(item.get("price", 0)) * int(item.get("quantity", item.get("qyt", 1)))
                for item in items
            )

            total = subtotal + delivery_charge
            amount_paise = int(total * 100)

            # 🔥 FIX: create client here (not globally)
            rzp_client = get_razorpay_client()

            # 🔥 Razorpay order
            rzp_order = rzp_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
            })

            user = request.user if request.user.is_authenticated else None

            order = Order.objects.create(
                user=user,
                amount=total,
                currency="INR",
                status="PENDING",
                razorpay_order_id=rzp_order["id"],
                delivery_address=delivery_address,
                delivery_charge=delivery_charge,
                latitude=latitude,
                longitude=longitude,
            )

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product_id=str(item.get("product_id") or item.get("id") or ""),
                    name=item.get("name", ""),
                    price=float(item.get("price", 0)),
                    quantity=int(item.get("quantity", item.get("qyt", 1))),
                    image=item.get("image", ""),
                    category=item.get("category", ""),
                )

            return Response({
                "order_id": str(order.id),
                "razorpay_order_id": rzp_order["id"],
                "amount": amount_paise,
                "currency": "INR",
                "key": settings.RAZORPAY_KEY_ID,
            })

        except Exception as e:
            logger.error("Create order error: %s", e)
            return Response({"error": str(e)}, status=500)


# ───────────────────────────────────────────────
# VERIFY PAYMENT
# ───────────────────────────────────────────────
class VerifyPaymentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        try:
            razorpay_order_id = data.get("razorpay_order_id")
            razorpay_payment_id = data.get("razorpay_payment_id")
            razorpay_signature = data.get("razorpay_signature")

            if not razorpay_order_id:
                return Response({"error": "Invalid order id"}, status=400)

            order = Order.objects.get(razorpay_order_id=razorpay_order_id)

            payload = f"{razorpay_order_id}|{razorpay_payment_id}"

            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, razorpay_signature):
                order.status = "FAILED"
                order.save()
                return Response({"error": "Payment verification failed"}, status=400)

            order.status = "SUCCESS"
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.save()

            return Response({"message": "Payment successful"})

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        except Exception as e:
            logger.error("Verify payment error: %s", e)
            return Response({"error": str(e)}, status=500)


# ───────────────────────────────────────────────
# ORDER STATUS
# ───────────────────────────────────────────────
class OrderStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)

            return Response({
                "order_id": str(order.id),
                "status": order.status,
                "amount": order.amount,
                "created_at": order.created_at,
            })

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)


# ───────────────────────────────────────────────
# WEBHOOK
# ───────────────────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print("Webhook received")
        return Response({"status": "received"})