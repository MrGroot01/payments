### FILE: backend/payments/models.py

import uuid
from django.db import models
from django.contrib.auth.models import User


class Order(models.Model):
    STATUS_CHOICES = [
        ("PENDING",    "Pending"),
        ("PROCESSING", "Processing"),
        ("SUCCESS",    "Success"),
        ("FAILED",     "Failed"),
        ("REFUNDED",   "Refunded"),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    amount        = models.DecimalField(max_digits=10, decimal_places=2)   # in INR
    currency      = models.CharField(max_length=10, default="INR")
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    # Razorpay identifiers
    razorpay_order_id   = models.CharField(max_length=100, blank=True, null=True, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature  = models.CharField(max_length=200, blank=True, null=True)

    # Delivery
    delivery_address = models.TextField(blank=True)
    delivery_charge  = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id} | {self.user.username} | ₹{self.amount} | {self.status}"


class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_id = models.CharField(max_length=100)       # ID from your product API
    name       = models.CharField(max_length=255)
    price      = models.DecimalField(max_digits=10, decimal_places=2)
    quantity   = models.PositiveIntegerField(default=1)
    image      = models.URLField(blank=True)
    category   = models.CharField(max_length=50, blank=True)

    def get_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.name} x{self.quantity} in Order {self.order.id}"


class PaymentWebhookLog(models.Model):
    """Stores raw webhook payloads from Razorpay for auditing."""
    event      = models.CharField(max_length=100)
    payload    = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed  = models.BooleanField(default=False)

    def __str__(self):
        return f"Webhook: {self.event} at {self.received_at}"