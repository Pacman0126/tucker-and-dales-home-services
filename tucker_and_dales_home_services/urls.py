"""
URL configuration for tucker_and_dales_home_services project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from core import views as core_views
from scheduling import views as scheduling_views

urlpatterns = [
    # built-in login/password reset
    path("accounts/logout/", core_views.custom_logout, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    # path("", include("core.urls")),
    path("billing/", include("billing.urls", namespace="billing")),
    path("customers/", include("customers.urls")),
    path("schedule/", include("scheduling.urls")),

    # path("base-search/", core_views.base_search, name="base_search"),
]
