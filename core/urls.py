from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("newsletter/unsubscribe/<str:token>/",
         views.newsletter_unsubscribe, name="newsletter_unsubscribe"),
    path("newsletter/send-now/", views.newsletter_send_now,
         name="newsletter_send_now"),
    path("", views.home, name="home"),
]
