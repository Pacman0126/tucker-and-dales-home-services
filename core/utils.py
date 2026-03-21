from allauth.account.models import EmailAddress


def user_has_verified_email(user) -> bool:
    if not user.is_authenticated:
        return False

    return EmailAddress.objects.filter(
        user=user,
        email=user.email,
        verified=True,
    ).exists()


def user_can_bypass_email_verification(user) -> bool:
    if not user.is_authenticated:
        return False

    return user.is_staff or user.is_superuser
