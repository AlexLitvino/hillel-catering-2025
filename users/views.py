from typing import Any

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, routers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import User
from .services import ActivationService


# validation class based on existing model
class UserSerializer(serializers.ModelSerializer):
    # override default behavior here
    # these fields should be included to fields attribute
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "phone_number", "first_name", "last_name", "password", "role"]

    def validate(self, attrs: dict[str, Any]):
        """Change password to its hash to make Token-based authentication available"""
        attrs["password"] = make_password(attrs["password"])
        attrs["is_active"] = False

        return super().validate(attrs=attrs)


class UserActivationSerializer(serializers.Serializer):
    key = serializers.UUIDField()


class UserResendActivationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UsersAPIViewSet(viewsets.GenericViewSet):

    authentication_classes = [JWTAuthentication]
    # permission_classes = [permissions.AllowAny]  # was IsAuthenticate but user creation should be allowed without auth

    def get_permissions(self):
        # return super().get_permissisons()
        if self.action == "create":
            return [permissions.AllowAny()]
        elif self.action == "activate" or self.action == "resend_activation":
            return [permissions.AllowAny()]
        else:
            return [permissions.IsAuthenticated()]

    def list(self, request: Request):
        # instead of this:
        # user = request.user
        # data = {
        #     "id": user.id,
        #     "email": user.email,
        #     "first_name": user.first_name,
        #     "last_name": user.last_name,
        #     "phone": user.phone_number
        # }
        # return Response(data, status=200)
        # use this:
        return Response(UserSerializer(request.user).data, status=200)

    @transaction.atomic
    def create(self, request: Request):
        # to validate data
        serializer = UserSerializer(data=request.data)
        # if not serializer.is_valid():  # generates error in case of any error during serialization
        #     return Response()  # with errors
        serializer.is_valid(raise_exception=True)
        serializer.save()  # can't be saved before validation (serializer.is_valid()), it returns instance

        email = serializer.instance.email
        # Activation process
        activation_service = ActivationService(
            email=serializer.instance.email
            # email = getattr(serializer.instance, "email")
        )
        activation_key = activation_service.create_activation_key()

        activation_service.save_activation_information(user_id=serializer.instance.id, activation_key=activation_key)

        ActivationService.send_user_activation_email.delay(email, activation_key=activation_key)

        return Response(UserSerializer(serializer.instance).data, status=201)

    @action(methods=["POST"], detail=False)
    def activate(self, request: Request) -> Response:
        serializer = UserActivationSerializer(data=request.data)
        serializer.is_valid()

        activation_service = ActivationService()

        try:
            activation_service.activate_user(activation_key=serializer.validated_data["key"])
        except ValueError as error:
            raise ValidationError("Activation link is expired") from error

        return Response(data=None, status=204)

    @action(methods=["POST"], detail=False)
    def resend_activation(self, request: Request):
        serializer = UserResendActivationSerializer(data=request.data)
        serializer.is_valid()

        email = serializer.validated_data["email"]
        user_id = get_object_or_404(User, email=email).id
        is_active = get_object_or_404(User, email=email).is_active

        if is_active:
            raise ValidationError("User already activated")

        activation_service = ActivationService(email=email)
        activation_key = activation_service.create_activation_key()

        activation_service.save_activation_information(user_id=user_id, activation_key=activation_key)

        ActivationService.send_user_activation_email.delay(email, activation_key=activation_key)

        return Response(data=None, status=204)


router = routers.DefaultRouter()
router.register(r"", UsersAPIViewSet, basename="user")
