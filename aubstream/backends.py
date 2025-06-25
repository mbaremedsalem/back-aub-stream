# backends.py
from django.contrib.auth.backends import BaseBackend
from .models import AmUsersLocal

class CustomAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            user = AmUsersLocal.objects.get(username=username)
            if user.check_password(password):
                return user
        except AmUsersLocal.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return AmUsersLocal.objects.get(username=user_id)
        except AmUsersLocal.DoesNotExist:
            return None