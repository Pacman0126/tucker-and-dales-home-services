from django.urls import path
from . import views

app_name = "scheduling"

urlpatterns = [
    # =========================================================
    # 🔎 SEARCH ROUTES
    # =========================================================
    path("unlock-address/", views.unlock_address, name="unlock_address"),
    path("search/date/", views.search_by_date, name="search_by_date"),
    path("search/timeslot/", views.search_by_time_slot,
         name="search_by_time_slot"),

]
