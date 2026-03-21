from functools import wraps

from django.contrib import messages
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
