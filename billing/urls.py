from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    # 🧾 Admin Views
    path("admin/all-payments/", views.all_payments_admin,
         name="all_payments_admin"),
    path("refund/<int:pk>/", views.refund_payment, name="refund_payment"),

    # 💳 Customer Checkout & Payments
    path("checkout/", views.checkout_summary, name="checkout"),
    path("create-checkout-session/", views.create_checkout_session,
         name="create_checkout_session"),
    path("success/", views.payment_success, name="payment_success"),
    path("cancel/", views.payment_cancel, name="payment_cancel"),

    # 📜 Payment History
    path("history/", views.payment_history, name="payment_history"),

    # 🌐 Stripe Webhook
    path("webhook/", views.stripe_webhook, name="stripe_webhook"),

    # =========================================================
    # 🛒 CART ROUTES
    # =========================================================
    # full-page cart (optional)
    path("cart/", views.cart_detail, name="cart_detail"),
    # AJAX add endpoint
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/remove/", views.cart_remove,
         name="cart_remove"),   # AJAX remove endpoint
    path("cart/clear/", views.cart_clear,
         name="cart_clear"),      # AJAX clear endpoint
]
