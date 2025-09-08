from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from food.models import Dish, Restaurant

User = get_user_model()


class DishesAPITestCase(TestCase):
    def setUp(self):
        self.anon = APIClient()
        self.client = APIClient()

        self.john = User.objects.create_user(email="john@email.com", password="@Dm1n#LKJ")
        self.john.is_active = True  # activate user
        self.john.save()

        # Obtain JWT token
        response = self.client.post(
            reverse("obtain_token"),
            {
                "email": "john@email.com",
                "password": "@Dm1n#LKJ",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data["access"]

        # Set the JWT token in the Authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Log in the user
        self.restaurant1 = Restaurant.objects.create(name="Pizza Hut", address="123 Main St")
        self.restaurant2 = Restaurant.objects.create(name="Dominos", address="456 Elm St")

        self.disha = Dish.objects.create(restaurant=self.restaurant1, name="Dish A", price=100)
        self.dishb = Dish.objects.create(restaurant=self.restaurant1, name="Dish B", price=150)
        self.dishc = Dish.objects.create(restaurant=self.restaurant2, name="Dish C", price=200)
        self.dishd = Dish.objects.create(restaurant=self.restaurant2, name="Dish D", price=250)

    def test_get_dishes_anonymous(self):
        response = self.anon.get(reverse("food-dishes"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_dishes_authorized(self):
        response = self.client.get(reverse("food-dishes"))
        dishes = response.json()
        total_dishes = len(dishes)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(total_dishes, 4)
