import pytest

# from django.contrib.auth import get_user_model
# User = get_user_model()


@pytest.fixture
def john(django_user_model):
    user = django_user_model.objects.create_user(
        email="john@email.com",
        password="password",
        phone_number="+3809711",
        first_name="John",
        last_name="Doe",
        is_active=True,
    )

    return user
