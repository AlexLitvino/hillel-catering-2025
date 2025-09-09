import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

User = get_user_model()


class UserTestCase(TestCase):
    def test_user_creation(self):
        # setup data
        payload = {
            "email": "john@email.com",
            "password": "@Dm1n#LKJ",
            "first_name": "John",
            "last_name": "Doe",
        }

        # action
        User.objects.create_user(**payload)

        # evaluate
        john = User.objects.first()
        total_users = User.objects.count()

        self.assertEqual(total_users, 1, f"Invalid users amount: {total_users}")

        for attr, value in payload.items():
            if attr == "password":
                continue

            assert getattr(john, attr) == value



@pytest.mark.parametrize(
    "payload",
    (
        {
            # email is the same
            "email": "john@email.com",
            "password": "@Dm1n#LKJ",
            "phone_number": "different",
        },
        {
            # phone is the same
            "email": "marry@email.com",
            "password": "@Dm1n#LKJ",
            "phone_number": "+3809711",
        },
    ),
)
@pytest.mark.django_db
def test_user_duplicate(john, payload):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            User.objects.create_user(**payload)

    assert User.objects.count() == 1
