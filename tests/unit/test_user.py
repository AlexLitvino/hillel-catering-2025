from django.contrib.auth import get_user_model
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
