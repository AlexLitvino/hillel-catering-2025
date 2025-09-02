from enum import StrEnum, auto

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Role(StrEnum):
    ADMIN = auto()
    SUPPORT = auto()
    DRIVER = auto()
    CUSTOMER = auto()

    @classmethod
    def choises(cls):
        results = []
        for item in cls:
            _element: tuple[str, str] = (item.value, item.name.lower().capitalize())
            results.append(_element)

        return results


class UserManager(BaseUserManager):

    def create_user(self, email: str, password: str, **extra_fields):
        """Create and save USER with passed parameters"""
        email = self.normalize_email(email)
        password = make_password(password)  # hashing password

        extra_fields["is_active"] = False
        extra_fields["is_staff"] = False
        extra_fields["is_superuser"] = False
        extra_fields["role"] = Role.CUSTOMER

        user = self.model(email=email, password=password, **extra_fields)  # aka User() - instance of table
        user.save()

        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        """Create and save SUPERUSER with passed parameters"""
        email = self.normalize_email(email)
        password = make_password(password)  # hashing password

        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["role"] = Role.ADMIN

        user = self.model(email=email, password=password, **extra_fields)  # aka User() - instance of table
        user.save()

        return user


# Create your models here.
class User(AbstractBaseUser, PermissionsMixin):

    class Meta:
        db_table = "users"

    objects = UserManager()

    email = models.EmailField(max_length=100, unique=True, null=False)
    phone_number = models.CharField(max_length=10, unique=True, null=False)
    first_name = models.CharField(max_length=30, null=False)
    last_name = models.CharField(max_length=50, null=False)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # choices - is to create dropdown
    role = models.CharField(max_length=50, default=Role.CUSTOMER, choices=Role.choises())

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"  # TODO: why email?
    REQUIRED_FIELDS = []  # TODO: why it is empty?
