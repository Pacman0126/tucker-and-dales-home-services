from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    # 💳 Checkout & Payments
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/summary/", views.checkout_summary, name="checkout_summary"),
    path("create-checkout-session/", views.create_checkout_session,
         name="create_checkout_session"),
    path("success/", views.payment_success, name="payment_success"),
    path("cancel/", views.payment_cancel, name="payment_cancel"),
    path("payment/history/", views.payment_history, name="payment_history"),
    #     path("payment/receipt/<int:pk>/",
    #          views.payment_receipt_pdf, name="payment_receipt_pdf"),
    # path("download-receipt/", views.download_receipt, name="download_receipt"),
    path("receipt/pdf/<int:pk>/", views.download_receipt_pdf,
         name="download_receipt_pdf"),
    # 🛒 Cart
    path("cart/add/", views.cart_add, name="cart_add"),
    path("cart/remove/", views.cart_remove, name="cart_remove"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    path("cart/detail/", views.cart_detail, name="cart_detail"),

    # 🧾 Admin & Stripe Webhooks
    path("admin/all-payments/", views.all_payments_admin,
         name="all_payments_admin"),
    path("admin/refund/<int:pk>/", views.refund_payment, name="refund_payment"),
    path("webhook/", views.stripe_webhook, name="stripe_webhook"),
]
