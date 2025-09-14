"""
-------------------------------------------------------------------------------------------------
| Method | Endpoint                 | Anonymous                | Authorized                     |
-------------------------------------------------------------------------------------------------
| POST   | /auth/token              | 200                      | 200                            |
| POST   | /food/create-dishes      | 401                      | 201/403                        |
| GET    | /food/dishes             | 200                      | 200                            | For anonymous returns 401 instead 200
| GET    | /food/orders             | 401                      | 200                            |
| POST   | /food/orders             | 401                      | 201                            |
| GET    | /food/orders/{id}        | 401                      | 200 (exist) / 404 (not exists) | In real, returns 500 for non-existing for authorized
| GET    | /users/                  | 401                      | 200                            |
| POST   | /users/                  | 201                      | ???                            | Code returns 201 for authorized, but should?
| POST   | /users/activate/         | 204/400(link expired)    | ???                            |
| POST   | /users/resend_activation | 204/400 (alr activ)/404  | ???                            |
-------------------------------------------------------------------------------------------------
??? - should this endpoints work for authorized user?

Test if your endpoints work "good-enough" according to your permissions restrictions.
Each endpoint must be tested to make sure that some endpoints are not exposed to unexpected user roles.
"""

from datetime import date, timedelta

import pytest

@pytest.mark.django_db
@pytest.mark.parametrize("is_authorized, method, url, payload, expected_status", [
    (False, "post", "/auth/token/", {"email": "john.doe@test.com", "password": "password123"}, 200),
    (False, "post", "/food/create-dishes/", {"name": "Nesquick", "price": 11}, 401),
    (True, "post", "/food/create-dishes/", {"name": "Cacao", "price": 11}, 201),
    (False, "get", "/food/dishes/", None, 200),  # FAIL: returns 401 for anonymous instead of 200
    (True, "get", "/food/dishes/", None, 200),
    (False, "get", "/food/orders/", None, 401),
    (True, "get", "/food/orders/", None, 200),
    (False, "post", "/food/orders/", {"eta": date.today() +  timedelta(days=2), "delivery_provider": "uklon"}, 401),
    #(True, "post", "/food/orders/", {"eta": date.today() +  timedelta(days=2), "delivery_provider": "uklon"}, 201), # fails because provider is not mocked, tested in test_order.py
    (False, "get", "/food/orders/ID/", None, 401),
    (True, "get", "/food/orders/ID/", None, 200),
    (False, "get", "/users/", None, 401),
    (True, "get", "/users/", None, 200),
    (False, "post", "/users/", {"email": "new_user@test.com", "phone_number": "4234567896", "first_name": "Jack", "last_name": "Black", "password": "customer"}, 201),
    (False, "post", "/users/activate/", None, 204),
    (False, "post", "/users/resend_activation/", None, 204),
])
def test_endpoints_permissions(is_authorized, method, url, payload, expected_status, api_client, authorized_registered_user,
                               nominal_user_data, get_token, nominal_restaurant, nominal_dish, not_activated_user, nominal_order, get_activation_key):

    if is_authorized:
        token = get_token(nominal_user_data["email"], nominal_user_data["password"])
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    if url == "/food/create-dishes/":
        payload.update({"restaurant": nominal_restaurant.pk})
    elif url == "/food/orders/" and method == "post":
        payload.update({"items": [{"dish": nominal_dish.pk, "quantity": 2}]})
    elif url == "/food/orders/ID/":
        url = url.replace("ID", str(nominal_order.pk))
    elif url == "/users/activate/":
        payload = {"key": get_activation_key(not_activated_user)}
    elif url == "/users/resend_activation/":
        payload = {"email": not_activated_user.email}

    response = getattr(api_client, method)(url, data=payload, format="json")
    assert response.status_code == expected_status, (f"For {'authorized' if is_authorized else 'anonymous'} user {method.upper()} {url} "
                                                     f"expected to get status {expected_status}, but got {response.status_code}")
