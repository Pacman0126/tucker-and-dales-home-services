"""
URL configuration for tucker_and_dales_home_services project.
"""

from django.contrib import admin
from django.urls import include, path
from core.views import robots_txt
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap


def test_500(request):
    """
    Temporary route to trigger a real server error for testing.
    Remove this route after verifying the custom 500 page works.
    """
    raise Exception("Deliberate test 500")


handler404 = "core.views.custom_404"
handler500 = "core.views.custom_500"
sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps},
         name="django.contrib.sitemaps.views.sitemap"),
    path("", include(("core.urls", "core"), namespace="core")),
    path("billing/", include(("billing.urls", "billing"),
                             namespace="billing")),
    path(
        "customers/",
        include(("customers.urls", "customers"), namespace="customers"),
    ),
    path(
        "schedule/",
        include(("scheduling.urls", "scheduling"), namespace="scheduling"),
    ),


    # TEMPORARY: remove after testing custom 500 handling
    path("test-500/", test_500, name="test_500"),
]
