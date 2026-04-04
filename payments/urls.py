from django.urls import path
from .views import CreateOrderView, VerifyPaymentView, OrderStatusView, RazorpayWebhookView
 
urlpatterns = [
    # 1. Create a Razorpay order
    path("create-order/",        CreateOrderView.as_view(),    name="create-order"),
 
    # 2. Verify payment after Razorpay checkout
    path("verify/",              VerifyPaymentView.as_view(),  name="verify-payment"),
 
    # 3. Poll order status from React
    path("order/<uuid:order_id>/", OrderStatusView.as_view(), name="order-status"),
 
    # 4. Razorpay webhook (add this URL in Razorpay Dashboard → Webhooks)
    path("webhook/",             RazorpayWebhookView.as_view(), name="razorpay-webhook"),
]