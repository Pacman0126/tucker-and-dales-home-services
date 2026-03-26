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
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView


def test_500(request):
    """
    Temporary route to trigger a real server error for testing.
    Remove this route after verifying the custom 500 page works.
    """
    raise Exception("Deliberate test 500")


handler404 = "core.views.custom_404"
handler500 = "core.views.custom_500"

urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(url=static("images/favicon.ico"), permanent=True),
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include(("core.urls", "core"), namespace="core")),
    path("billing/", include(("billing.urls", "billing"), namespace="billing")),
    path(
        "customers/",
        include(("customers.urls", "customers"), namespace="customers"),
    ),
    path(
        "schedule/",
        include(("scheduling.urls", "scheduling"), namespace="scheduling"),
    ),

    # # TEMPORARY: remove after testing custom 500 handling
    # path("test-500/", test_500, name="test_500"),
]
