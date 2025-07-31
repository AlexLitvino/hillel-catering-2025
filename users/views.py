from typing import Any

from rest_framework import  viewsets, routers, permissions, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.hashers import make_password

from .models import User

# validation class based on existing model
class UserSerializer(serializers.ModelSerializer):
    # override default behavior here
    # these fields should be included to fields attribute
    password = serializers.CharField(write_only=True)
    role = serializers.CharField(read_only=True)
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "password",
            "role"
        ]

    def validate(self, attrs: dict[str, Any]):
        """Change password to its hash to make Token-based authentication available"""
        attrs["password"] = make_password(attrs["password"])

        return super().validate(attrs=attrs)

class UsersAPIViewSet(viewsets.GenericViewSet):

    authentication_classes = [JWTAuthentication]
    #permission_classes = [permissions.AllowAny]  # was IsAuthenticate but user creation should be allowed without auth

    def get_permissions(self):
        #return super().get_permissisons()
        if self.action == "create":
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


    def create(self, request: Request):
        # to validate data
        serializer = UserSerializer(data=request.data)
        # if not serializer.is_valid():  # generates error in case of any error during serialization
        #     return Response()  # with errors
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()  # can't be saved before validation (serializer.is_valid())
        return Response(UserSerializer(serializer.instance).data, status=201)


router = routers.DefaultRouter()
router.register("", UsersAPIViewSet, basename="user")


