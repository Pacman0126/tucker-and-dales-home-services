# core/backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Allows users to authenticate with either their username or email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        # Try username or email lookup
        try:
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
