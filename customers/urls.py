from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path("", views.customer_list, name="customer_list"),
    path("<int:pk>/", views.customer_detail, name="customer_detail"),
    path("new/", views.customer_create, name="customer_create"),
]
