from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    path("all/", views.all_payments_admin, name="all_payments_admin"),
    path("create-checkout-session/", views.create_checkout_session,
         name="create_checkout_session"),
    path("cancel/", views.payment_cancel, name="payment_cancel"),
    path("history/", views.payment_history, name="payment_history"),
    path("refund/<int:pk>/", views.refund_payment, name="refund_payment"),
    path("success/", views.payment_success, name="payment_success"),
    path("webhook/", views.stripe_webhook, name="stripe_webhook"),
]
