from django.contrib import admin
from .models import Order, OrderItem, PaymentWebhookLog


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "amount",
        "status",
        "razorpay_payment_id",
        "created_at",
    ]

    list_filter = ["status", "created_at"]

    search_fields = [
        "id",
        "user__username",
        "razorpay_payment_id",
        "razorpay_order_id",
    ]

    inlines = [OrderItemInline]

    readonly_fields = [
        "razorpay_order_id",
        "razorpay_payment_id",
        "razorpay_signature",
        "created_at",
        "updated_at",
    ]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "name", "price", "quantity"]
    search_fields = ["name", "order__id"]


@admin.register(PaymentWebhookLog)
class PaymentWebhookLogAdmin(admin.ModelAdmin):
    list_display = ["event", "received_at", "processed"]
    readonly_fields = ["payload", "received_at"]