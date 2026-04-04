### FILE: backend/payments/serializers.py

from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OrderItem
        fields = ["product_id", "name", "price", "quantity", "image", "category"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = [
            "id", "amount", "currency", "status",
            "razorpay_order_id", "razorpay_payment_id",
            "delivery_address", "delivery_charge",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "razorpay_order_id", "razorpay_payment_id", "created_at", "updated_at"]


class CreateOrderSerializer(serializers.Serializer):
    """Input: cart items + delivery info."""
    items = serializers.ListField(
        child=serializers.DictField(), min_length=1
    )
    delivery_address = serializers.CharField(max_length=500)
    delivery_charge  = serializers.DecimalField(max_digits=6, decimal_places=2, default=0)


class VerifyPaymentSerializer(serializers.Serializer):
    """Input: Razorpay response after payment."""
    razorpay_order_id   = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature  = serializers.CharField()