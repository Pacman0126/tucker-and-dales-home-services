from django.urls import path
from . import views

app_name = "scheduling"

urlpatterns = [
    path("search/date/", views.search_by_date, name="search_by_date"),
    path("search/timeslot/", views.search_by_time_slot,
         name="search_by_time_slot"),
]
