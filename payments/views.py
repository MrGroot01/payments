### FILE: backend/payments/views.py

import hmac
import hashlib
import json
import logging

import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order, OrderItem, PaymentWebhookLog
from .serializers import CreateOrderSerializer, OrderSerializer, VerifyPaymentSerializer

logger = logging.getLogger(__name__)

# ── Razorpay client (initialised once) ──────────────────────────────────────
rzp_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


# ────────────────────────────────────────────────────────────────────────────
# 1.  POST /api/payments/create-order/
#     Authenticated user sends cart → Django creates Razorpay order.
# ────────────────────────────────────────────────────────────────────────────
class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = CreateOrderSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data

        # 1a. Calculate total from items (always recompute server-side!)
        subtotal = sum(
            float(item["price"]) * int(item.get("quantity", item.get("qyt", 1)))
            for item in data["items"]
        )
        total = subtotal + float(data["delivery_charge"])
        amount_paise = int(total * 100)           # Razorpay expects paise

        # 1b. Create Razorpay order
        try:
            rzp_order = rzp_client.order.create({
                "amount":   amount_paise,
                "currency": "INR",
                "receipt":  f"receipt_{request.user.id}",
                "payment_capture": 1,             # auto-capture
            })
        except Exception as exc:
            logger.error("Razorpay order creation failed: %s", exc)
            return Response(
                {"detail": "Payment gateway error. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 1c. Save PENDING order in DB
        order = Order.objects.create(
            user=request.user,
            amount=total,
            currency="INR",
            status="PENDING",
            razorpay_order_id=rzp_order["id"],
            delivery_address=data["delivery_address"],
            delivery_charge=data["delivery_charge"],
        )

        # 1d. Save order items
        for item in data["items"]:
            OrderItem.objects.create(
                order=order,
                product_id=str(item.get("id", "")),
                name=item.get("name", ""),
                price=float(item.get("price", 0)),
                quantity=int(item.get("quantity", item.get("qyt", 1))),
                image=item.get("image", ""),
                category=item.get("category", ""),
            )

        return Response({
            "order_id":        order.id,
            "razorpay_order_id": rzp_order["id"],
            "amount":          amount_paise,
            "currency":        "INR",
            "key":             settings.RAZORPAY_KEY_ID,   # send public key to frontend
        }, status=status.HTTP_201_CREATED)


# ────────────────────────────────────────────────────────────────────────────
# 2.  POST /api/payments/verify/
#     After Razorpay checkout closes, frontend sends 3 IDs → Django verifies.
# ────────────────────────────────────────────────────────────────────────────
class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = VerifyPaymentSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        d = ser.validated_data

        # 2a. Fetch the order
        try:
            order = Order.objects.get(
                razorpay_order_id=d["razorpay_order_id"],
                user=request.user,
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        # 2b. Signature verification (HMAC-SHA256)
        #     signature = HMAC_SHA256(razorpay_order_id + "|" + razorpay_payment_id, secret)
        payload  = f"{d['razorpay_order_id']}|{d['razorpay_payment_id']}"
        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, d["razorpay_signature"]):
            order.status = "FAILED"
            order.save(update_fields=["status"])
            logger.warning("Signature mismatch for order %s", order.id)
            return Response({"detail": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        # 2c. Update order
        order.razorpay_payment_id = d["razorpay_payment_id"]
        order.razorpay_signature  = d["razorpay_signature"]
        order.status              = "SUCCESS"
        order.save(update_fields=["razorpay_payment_id", "razorpay_signature", "status"])

        logger.info("Payment verified: order %s, payment %s", order.id, d["razorpay_payment_id"])
        return Response({"detail": "Payment verified.", "order_id": str(order.id)}, status=status.HTTP_200_OK)


# ────────────────────────────────────────────────────────────────────────────
# 3.  GET /api/payments/order/<order_id>/
#     Frontend polls this to get the current order status.
# ────────────────────────────────────────────────────────────────────────────
class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related("items").get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


# ────────────────────────────────────────────────────────────────────────────
# 4.  POST /api/payments/webhook/
#     Razorpay calls this URL for real-time events (payment.captured, etc.)
#     Must be publicly accessible — no authentication middleware.
# ────────────────────────────────────────────────────────────────────────────
@method_decorator(csrf_exempt, name="dispatch")
class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]     # Razorpay doesn't send user tokens
    authentication_classes = []         # skip DRF auth

    def post(self, request):
        # 4a. Verify webhook signature
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        received_sig   = request.headers.get("X-Razorpay-Signature", "")
        body_bytes     = request.body

        expected_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, received_sig):
            logger.warning("Invalid webhook signature received")
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        # 4b. Parse payload
        try:
            payload = json.loads(body_bytes)
        except json.JSONDecodeError:
            return Response({"detail": "Bad JSON."}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get("event", "")

        # 4c. Log the webhook
        log = PaymentWebhookLog.objects.create(event=event, payload=payload)

        # 4d. Handle events
        if event == "payment.captured":
            self._handle_payment_captured(payload)
            log.processed = True
            log.save(update_fields=["processed"])

        elif event == "payment.failed":
            self._handle_payment_failed(payload)
            log.processed = True
            log.save(update_fields=["processed"])

        elif event == "refund.created":
            self._handle_refund(payload)
            log.processed = True
            log.save(update_fields=["processed"])

        return Response({"status": "ok"})

    # ── internal helpers ────────────────────────────────────────────────────

    def _handle_payment_captured(self, payload):
        try:
            rzp_order_id = payload["payload"]["payment"]["entity"]["order_id"]
            rzp_pay_id   = payload["payload"]["payment"]["entity"]["id"]
            order = Order.objects.get(razorpay_order_id=rzp_order_id)
            if order.status != "SUCCESS":          # don't downgrade a verified order
                order.status              = "SUCCESS"
                order.razorpay_payment_id = rzp_pay_id
                order.save(update_fields=["status", "razorpay_payment_id"])
                logger.info("Webhook: captured order %s", order.id)
        except (Order.DoesNotExist, KeyError) as exc:
            logger.error("Webhook payment.captured error: %s", exc)

    def _handle_payment_failed(self, payload):
        try:
            rzp_order_id = payload["payload"]["payment"]["entity"]["order_id"]
            order = Order.objects.get(razorpay_order_id=rzp_order_id)
            if order.status == "PENDING":
                order.status = "FAILED"
                order.save(update_fields=["status"])
                logger.info("Webhook: failed order %s", order.id)
        except (Order.DoesNotExist, KeyError) as exc:
            logger.error("Webhook payment.failed error: %s", exc)

    def _handle_refund(self, payload):
        try:
            rzp_pay_id = payload["payload"]["refund"]["entity"]["payment_id"]
            order = Order.objects.get(razorpay_payment_id=rzp_pay_id)
            order.status = "REFUNDED"
            order.save(update_fields=["status"])
            logger.info("Webhook: refunded order %s", order.id)
        except (Order.DoesNotExist, KeyError) as exc:
            logger.error("Webhook refund.created error: %s", exc)