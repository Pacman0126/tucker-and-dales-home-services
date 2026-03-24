from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect

from .utils import user_can_bypass_email_verification, user_has_verified_email


def verified_email_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect("account_login")

        if user_can_bypass_email_verification(user):
            return view_func(request, *args, **kwargs)

        if user_has_verified_email(user):
            return view_func(request, *args, **kwargs)

        messages.warning(
            request,
            "Please verify your email address before accessing this page.",
        )
        return redirect("account_email_verification_sent")

    return _wrapped_view


def login_required_json(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )

        if wants_json:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Please register or log in to add services to your cart.",
                    "redirect_url": "/accounts/signup/",
                },
                status=401,
            )
        return redirect("account_login")

    return _wrapped_view
