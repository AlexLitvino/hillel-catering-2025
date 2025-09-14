from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from food.models import Dish, Order, Restaurant
from users.services import ActivationService

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def nominal_user_data():
    return {
    "email": "john.doe@test.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    }


@pytest.fixture
def not_activated_user_data():
    return {
    "email": "john.doe2@test.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "1111111111"
    }


@pytest.fixture
def authorized_registered_user(django_user_model, nominal_user_data):
    user =  django_user_model.objects.create_user(**nominal_user_data)
    user.is_active = True
    user.role = 'admin'
    user.save()
    return user

@pytest.fixture
def not_activated_user(django_user_model, not_activated_user_data):
    user =  django_user_model.objects.create_user(**not_activated_user_data)
    user.save()
    return user


@pytest.fixture
def get_token(api_client):
    def _get_token(email, password):
        response = api_client.post("/auth/token/", {
            "email": email,
            "password": password
        }, format="json")
        assert response.status_code == 200, "Token wasn't obtained"
        return response.json()["access"]
    return _get_token

@pytest.fixture
def nominal_restaurant():
    restaurant = Restaurant.objects.create(name="Silpo", address="Addr1")
    return restaurant

@pytest.fixture
def nominal_dish(nominal_restaurant):
    dish = Dish.objects.create(name="Cacao", price=11, restaurant=nominal_restaurant)
    return dish

@pytest.fixture
def nominal_order(authorized_registered_user, nominal_restaurant, nominal_dish):
    order = Order.objects.create(status="NOT_STARTED", delivery_provider="uklon", eta= date.today() +  timedelta(days=2), total=100, user=authorized_registered_user)
    return order

@pytest.fixture
def get_activation_key(request):
    def _get_activation_key(user):
        activation_service = ActivationService(email=user.email)
        activation_key = activation_service.create_activation_key()
        activation_service.save_activation_information(user_id=user.pk, activation_key=activation_key)

        def remove_activation_key():
            activation_service.cache.delete(namespace="activation", key=activation_key)
        request.addfinalizer(remove_activation_key)

        return activation_key

    return _get_activation_key
