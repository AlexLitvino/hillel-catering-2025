from datetime import date, timedelta

import pytest

from food.providers.silpo import OrderResponse as SilpoOrderResponse, OrderStatus as SilpoOrderStatus
from food.providers.uklon import OrderResponse as UklonOrderResponse, OrderStatus as UklonOrderStatus
from food.models import Order, OrderItem
from food.enums import OrderStatus

@pytest.mark.django_db
def test_order(api_client, authorized_registered_user, nominal_user_data, get_token, nominal_dish, mocker):

    # mocking Silpo service responses
    mock_create_silpo_order_response = SilpoOrderResponse(id="12345", status=SilpoOrderStatus.NOT_STARTED)
    mock_get_silpo_order_response = SilpoOrderResponse(id="12345", status=SilpoOrderStatus.FINISHED)
    mocker.patch("food.providers.silpo.Client.create_order", return_value=mock_create_silpo_order_response)
    mocker.patch("food.providers.silpo.Client.get_order", return_value=mock_get_silpo_order_response)

    # mocking Uklon service responses
    mock_create_uklon_order_response = UklonOrderResponse(id="12345", status=UklonOrderStatus.NOT_STARTED, location=(0.111, 0.333), addresses=["Addr1"], comments=["Comment"])
    mock_get_uklon_order_response = UklonOrderResponse(id="12345", status=UklonOrderStatus.DELIVERED, location=(0.111, 0.333), addresses=["Addr1"], comments=["Comment"])
    mocker.patch("food.providers.uklon.Client.create_order", return_value=mock_create_uklon_order_response)
    mocker.patch("food.providers.uklon.Client.get_order", return_value=mock_get_uklon_order_response)

    payload = {
        "eta": date.today() +  timedelta(days=2),
        "delivery_provider": "uklon",
        "items": [{"dish": nominal_dish.pk, "quantity": 2}]
    }

    token = get_token(nominal_user_data["email"], nominal_user_data["password"])
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = api_client.post("/food/orders/", data=payload, format="json")
    assert response.status_code == 201, f"Expected to get status 201, but got {response.status_code}"

    assert Order.objects.count() == 1, f"Expected 1 order to be created, but {Order.objects.count()} was created"

    expected_order = Order(
        status=OrderStatus.DELIVERED,
        delivery_provider=payload["delivery_provider"],
        eta=payload["eta"],
        total=payload["items"][0]["quantity"] * nominal_dish.price,
        user=authorized_registered_user)
    expected_order.pk = response.json()["id"]
    assert Order.objects.first() == expected_order

    assert OrderItem.objects.count() == 1, f"Expected 1 OrderItem in Order, but {OrderItem.objects.count()} was created"

    order_item = OrderItem.objects.first()
    expected_order_item = OrderItem(
        quantity=payload["items"][0]["quantity"],
        dish=nominal_dish,
        order=expected_order)
    expected_order_item.pk = order_item.pk  # OrderItem id is taken from DB and set to expected OrderItem to ignore it
    assert order_item == expected_order_item
