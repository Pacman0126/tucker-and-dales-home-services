from django.urls import path
from . import views

app_name = "scheduling"

urlpatterns = [
    # =========================================================
    # 🔎 SEARCH ROUTES
    # =========================================================
    path("search/date/", views.search_by_date, name="search_by_date"),
    path("search/timeslot/", views.search_by_time_slot,
         name="search_by_time_slot"),
    path("base-search/", views.base_search, name="base_search"),

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
