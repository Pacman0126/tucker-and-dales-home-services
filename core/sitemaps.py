from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        return [
            "core:home",
            "scheduling:search_by_date",
            "scheduling:search_by_time_slot",
            "billing:payment_history",
            "account_login",
            "account_signup",
        ]

    def location(self, item):
        return reverse(item)
