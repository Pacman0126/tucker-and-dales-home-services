from django.contrib import admin

from .models import Address, NewsletterSubscription


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "label", "line1", "city", "postal_code")
    search_fields = ("label", "line1", "city",
                     "postal_code", "owner__username")
    list_filter = ("city", "state", "country")


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "next_send_on",
        "unsubscribed",
        "created_at",
        "updated_at",
    )
    search_fields = ("user__username", "user__email", "token")
    list_filter = ("unsubscribed", "next_send_on", "created_at")
    readonly_fields = ("token", "created_at", "updated_at")
