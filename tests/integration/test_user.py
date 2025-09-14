from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.client import Client
from rest_framework import status

User = get_user_model()


class UserTestCase(TestCase):
    def test_john_creation(self):
        client = Client()
        payload = {
            "email": "john@email.com",
            "password": "@Dm1n#LKJ",
            "phone_number": "...",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = client.post(path="/users/", data=payload)

        john = User.objects.get(id=response.json()["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(john.first_name, response.json()["first_name"])
        self.assertEqual(john.last_name, response.json()["last_name"])