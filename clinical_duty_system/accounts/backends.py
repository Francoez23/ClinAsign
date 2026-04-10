from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameOrSchoolIdBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = (username or kwargs.get(user_model.USERNAME_FIELD) or '').strip()

        if not identifier or password is None:
            return None

        user = user_model._default_manager.filter(username__iexact=identifier).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        user = user_model._default_manager.filter(profile__student_id__iexact=identifier).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
