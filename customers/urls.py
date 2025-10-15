from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path("", views.customer_list, name="customer_list"),
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    path("<int:pk>/", views.customer_detail, name="customer_detail"),
    path("<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("<int:pk>/delete/", views.customer_delete, name="customer_delete"),
    path("register/", views.register, name="register"),

]
