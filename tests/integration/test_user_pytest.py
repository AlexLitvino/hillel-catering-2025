import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test.client import Client
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db  # to work with database
def test_john_creation(client: Client):  # built-in fixture. show django-pytest
    payload = {
        "email": "john@email.com",
        "phone_number": "+3809711",
        "password": "@Dm1n#LKJ",
        "first_name": "John",
        "last_name": "Doe",
    }

    response = client.post(path="/users/", data=payload)
    john = User.objects.get(id=response.json()["id"])

    assert response.status_code == status.HTTP_201_CREATED, response.json()
    assert User.objects.count() == 1
    assert john.id == response.json()["id"]
    assert john.first_name == response.json()["first_name"]
    assert john.last_name == response.json()["last_name"]
