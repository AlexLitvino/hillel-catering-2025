import uuid

from django.core.mail import send_mail
from django.conf import settings

from config import celery_app
from shared.cache import CacheService
from .models import User

class ActivationService:

    def __init__(self, email: str | None = None):
        self.email: str | None = email
        self.cache: CacheService = CacheService()

    def create_activation_key(self):
        # key = uuid.uuid3(settings.UUID_NAMESPACE, self.email)
        # OR
        key = uuid.uuid4()
        return key

    def save_activation_information(self, user_id: int, activation_key: str):
        """Save activation data to the cache
        1. Connect to the Cache Service
        2. Save structure to the Cache
        {
            "fevge-g25tg-42tg5455g-425g4g": {
                "user_id": 3
            }
        }
        3. Return None
        """
        payload = {
            "user_id": user_id
        }
        self.cache.set(namespace="activation", key=str(activation_key), value=payload, ttl=settings.ACTIVATION_EXPIRATION_TIME)
        return None

    @staticmethod
    @celery_app.task(queue="low_priority")
    def send_user_activation_email(email, activation_key: str):
        if email is None:
            raise ValueError("No email specified for user activation process")

        # SMTP Client Send Email Request
        activation_link = f"https://frontend.catering.com/activation/{activation_key}"
        send_mail(subject="User Activation",
                  message=f"Please activate your account: {activation_link}",
                  from_email="admin@catering.com",
                  recipient_list=[email])

    def activate_user(self, activation_key: str) -> None:
        user_cache_payload: dict | None = self.cache.get(namespace="activation", key=activation_key)

        if user_cache_payload is None:
            raise ValueError("No payload in cache")

        user = User.objects.get(id=user_cache_payload["user_id"])
        user.is_active = True
        user.save()
        # OR User.objects.filter(id=user...).update(is_active=True)
        self.cache.delete(namespace="activation", key=activation_key)

