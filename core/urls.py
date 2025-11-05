from django.urls import path
from . import views

urlpatterns = [
    # ... your existing core URLs ...
    path("newsletter/unsubscribe/<str:token>/",
         views.newsletter_unsubscribe, name="newsletter_unsubscribe"),
    path("newsletter/send-now/", views.newsletter_send_now,
         name="newsletter_send_now"),  # staff-only
]
