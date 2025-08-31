from dataclasses import dataclass, field, asdict
from time import sleep
from threading import Thread
import random

from django.db.models import QuerySet
from django.conf import settings

from shared.cache import CacheService
from config import celery_app

from food.providers import uklon, uber
from .enums import OrderStatus
from .mapper import RESTAURANT_EXTERNAL_TO_INTERNAL
from .models import Order, OrderItem, Restaurant
from .providers import kfc, silpo


@dataclass
class TrackingOrder:
    """
    {
        17: {  // internal Order.id
            restaurants: {
                1: {  // internal restaurant id
                    status: NOT_STARTED, // internal
                    external_id: 13,
                    request_body: {...},
                },
                2: {  // internal restaurant id
                    status: NOT_STARTED, // internal
                    external_id: edf055b8-06e8-40ed-ab35-300fef3e0a5d,
                    request_body: {...},
                },
            },
            delivery: {
                location: (..., ...),
                status: NOT STARTED, DELIVERY, DELIVERED
            }
        },
        18: ...
    }
    """
    restaurants: dict = field(default_factory=dict)
    delivery: dict = field(default_factory=dict)


def all_orders_cooked(order_id: int):
    cache = CacheService()
    tracking_order = TrackingOrder(**cache.get(namespace="orders", key=str(order_id)))
    print(f"Checking if all orders are cooked: internal_id = {order_id}, {tracking_order.restaurants}")

    if all((payload["status"] == OrderStatus.COOKED for _, payload in tracking_order.restaurants.items())):
        order = Order.objects.filter(id=order_id)
        order.update(status=OrderStatus.COOKED)
        #Order.objects.filter(id=order_id).update(status=OrderStatus.COOKED)
        print("✅ All orders are COOKED")

        # Start orders delivery
        schedule_delivery(order.first().id)
    else:
        print(f"Not all orders are cooked: {tracking_order=}")


def schedule_delivery(order_id):
    delivery_provider = Order.objects.filter(id=order_id).first().delivery_provider
    match delivery_provider.lower():
        case "uklon":
            order_delivery_by_uklon.delay(order_id)
        case "uber":
            order_delivery_by_uber.delay(order_id)
        case _:
            raise ValueError(f"Delivery provider {delivery_provider} is not available for processing")


@celery_app.task(queue="default")
def order_delivery_by_uklon(order_id: int):
    """Using Uklon provider - start processing delivery order."""
    print("🚚 DELIVERY PROCESSING STARTED (UKLON)")

    provider = uklon.Client()
    cache = CacheService()
    order = Order.objects.get(id=order_id)

    # update Order state
    order.status = OrderStatus.DELIVERY_LOOKUP
    order.save()

    # prepare data for the first request
    addresses: list[str] = []
    comments: list[str] = []

    for rest_name, address in order.delivery_meta():
        addresses.append(address)
        comments.append(f"Delivery to the {rest_name}")

    order.status = OrderStatus.DELIVERY
    order.save()

    _response: uklon.OrderResponse = provider.create_order(
        uklon.OrderRequestBody(addresses=addresses, comments=comments)
    )

    tracking_order = TrackingOrder(**cache.get("orders", str(order.pk)))
    tracking_order.delivery["status"] = OrderStatus.DELIVERY
    tracking_order.delivery["location"] = _response.location

    current_status: uklon.OrderStatus = _response.status

    while current_status != uklon.OrderStatus.DELIVERED:
        response = provider.get_order(_response.id)

        print(f"🚙 Uklon [{response.status}]: 📍 {response.location}")

        if current_status == response.status:
            sleep(1)
            continue

        current_status = response.status  # DELIVERY, DELIVERED

        tracking_order.delivery["location"] = response.location

        # update cache
        cache.set("orders", str(order_id), asdict(tracking_order))

    print(f"🏁 UKLON [{response.status}]: 📍 {response.location}")

    # update storage
    Order.objects.filter(id=order_id).update(status=OrderStatus.DELIVERED)

    # update the cache
    tracking_order.delivery["status"] = OrderStatus.DELIVERED
    cache.set("orders", str(order_id), asdict(tracking_order))

    print("✅ DONE with Delivery (Uklon)")


@celery_app.task(queue="default")
def order_delivery_by_uber(order_id: int):
    """Using Uber provider - start processing delivery order."""
    print("🚚 DELIVERY PROCESSING STARTED (UBER)")

    provider = uber.Client()
    cache = CacheService()
    order = Order.objects.get(id=order_id)

    # update Order state
    order.status = OrderStatus.DELIVERY_LOOKUP
    order.save()

    # prepare data for the first request
    addresses: list[str] = []
    comments: list[str] = []

    for rest_name, address in order.delivery_meta():
        addresses.append(address)
        comments.append(f"Delivery to the {rest_name}")

    # order.status = OrderStatus.DELIVERY
    # order.save()

    _response: uber.OrderResponse = provider.create_order(
        uber.OrderRequestBody(addresses=addresses, comments=comments)
    )

    # save mapping uber_id -> catering_id
    cache.set(namespace='uber_delivery', key=_response.id, value={"internal_order_id": order_id})

    # get and process tracking order
    tracking_order = TrackingOrder(**cache.get("orders", str(order.pk)))
    tracking_order.delivery["status"] = OrderStatus.DELIVERY
    tracking_order.delivery["location"] = _response.location

    # update cache
    cache.set("orders", str(order_id), asdict(tracking_order))

    delivered = False
    # read cache until status become Delivered
    while not delivered:
        sleep(1)

        tracking_order = TrackingOrder(
            **cache.get(namespace="orders", key=str(order_id))
        )

        if tracking_order.delivery["status"] == OrderStatus.DELIVERED:
            break


    # update storage
    Order.objects.filter(id=order_id).update(status=OrderStatus.DELIVERED)

    print("✅ DONE with Delivery (Uber)")


@celery_app.task(queue="high_priority")
def order_in_silpo(order_id: int, items: QuerySet[OrderItem]):
    """Short polling requests to the Silpo API

    NOTES
    get order from cache
    is external_id?
      no: make order
      yes: get order
    """
    client = silpo.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="Silpo")

    def get_internal_status(status: silpo.OrderStatus) -> OrderStatus:
        return RESTAURANT_EXTERNAL_TO_INTERNAL["silpo"][status]

    cooked = False
    while not cooked:
        sleep(1)  # just a delay

        # GET ITEM FROM THE CACHE
        tracking_order = TrackingOrder(
            **cache.get(namespace="orders", key=str(order_id))
        )
        # validate
        silpo_order = tracking_order.restaurants.get(str(restaurant.pk))
        if not silpo_order:
            raise ValueError("No Silpo in orders processing")

        # PRINT CURRENT STATUS
        print(f"CURRENT SILPO ORDER STATUS: {silpo_order['status']}")

        if not silpo_order["external_id"]:
            # ✨ MAKE THE FIRST REQUEST IF NOT STARTED
            response: silpo.OrderResponse = client.create_order(
                silpo.OrderRequestBody(
                    order=[
                        silpo.OrderItem(dish=item.dish.name, quantity=item.quantity)
                        for item in items
                    ]
                )
            )
            internal_status: OrderStatus = get_internal_status(response.status)

            # UPDATE CACHE WITH EXTERNAL ID AND STATE
            tracking_order.restaurants[str(restaurant.pk)] |= {
                "external_id": response.id,
                "status": internal_status,
            }
            cache.set(
                namespace="orders", key=str(order_id), value=asdict(tracking_order), ttl=settings.ORDER_COOKING_EXPIRATION_TIME
            )
        else:
            # ✨ IF ALREADY HAVE EXTERNAL ID - JUST RETRIEVE THE ORDER
            # PASS EXTERNAL SILPO ORDER ID
            response = client.get_order(silpo_order["external_id"])

            internal_status = get_internal_status(response.status)
            print(f"Tracking for Silpo Order with HTTP GET /orders. Status: {internal_status}")

            if silpo_order["status"] != internal_status:  # STATUS HAS CHANGED
                tracking_order.restaurants[str(restaurant.pk)][
                    "status"
                ] = internal_status
                print(f"Silpo order status changed to {internal_status}")
                cache.set(
                    namespace="orders", key=str(order_id), value=asdict(tracking_order), ttl=settings.ORDER_COOKING_EXPIRATION_TIME
                )

                # if started cooking
                if internal_status == OrderStatus.COOKING:
                    Order.objects.filter(id=order_id).update(status=OrderStatus.COOKING)

            # changed as all_orders_cooked changed to be behavioral function (doesn't return anything, change status)
            # if internal_status == OrderStatus.COOKED:
            #     print("🍳 ORDER IS COOKED")
            #     cooked = True
            #
            #     # 🚧 CHECK IF ALL ORDERS ARE COOKED
            #     if all_orders_cooked(order_id):
            #         # cache.set(
            #         #     namespace="orders",
            #         #     key=str(order_id),
            #         #     value=asdict(tracking_order),
            #         # )
            #         Order.objects.filter(id=order_id).update(status=OrderStatus.COOKED)

            if internal_status == OrderStatus.COOKED:
                cooked = True
                all_orders_cooked(order_id)

@celery_app.task(queue="high_priority")
def order_in_kfc(order_id: int, items):
    client = kfc.Client()
    cache = CacheService()
    restaurant = Restaurant.objects.get(name="KFC")

    def get_internal_status(status: kfc.OrderStatus) -> OrderStatus:
        return RESTAURANT_EXTERNAL_TO_INTERNAL["kfc"][status]

    # GET TRACKING ORDER FROM THE CACHE
    tracking_order = TrackingOrder(**cache.get(namespace="orders", key=str(order_id)))

    response: kfc.OrderResponse = client.create_order(
        kfc.OrderRequestBody(
            order=[kfc.OrderItem(dish=item.dish.name, quantity=item.quantity) for item in items]
        )
    )

    internal_status = get_internal_status(response.status)

    # UPDATE CACHE WITH EXTERNAL ID AND STATE
    tracking_order.restaurants[str(restaurant.pk)] |= {
        "external_id": response.id,
        "status": internal_status,
    }

    print(f"Created MOCKED KFC Order. External ID: {response.id}, Status: {internal_status}")
    cache.set(namespace="orders", key=str(order_id), value=asdict(tracking_order), ttl=settings.ORDER_COOKING_EXPIRATION_TIME)

    # save another item form Mapping to the Internal Order
    cache.set(
        namespace="kfc_orders",
        key=response.id,  # external KFC order id
        value={
            "internal_order_id": order_id,
        },
    )

    # 🚧 CHECK IF ALL ORDERS ARE COOKED
    if all_orders_cooked(order_id):
        cache.set(namespace="orders", key=str(order_id), value=asdict(tracking_order), ttl=settings.ORDER_COOKING_EXPIRATION_TIME)
        Order.objects.filter(id=order_id).update(status=OrderStatus.COOKED)


# Now building request body is implemented in specific function, but could be moved to separate function
# def build_request_body():
#     pass

def schedule_order(order: Order):
    # define services and data state
    cache = CacheService()
    tracking_order = TrackingOrder()

    items_by_restaurants = order.items_by_restaurant()
    for restaurant, items in items_by_restaurants.items():
        # update tracking order instance to be saved to the cache
        tracking_order.restaurants[str(restaurant.pk)] = {
            "external_id": None,
            "status": OrderStatus.NOT_STARTED,
        }

    # update cache instance only once in the end
    cache.set(namespace="orders", key=str(order.pk), value=asdict(tracking_order), ttl=settings.ORDER_COOKING_EXPIRATION_TIME)

    # start processing after cache is complete
    # threads = []
    for restaurant, items in items_by_restaurants.items():
        match restaurant.name.lower():
            case "silpo":
                #thread = Thread(target=order_in_silpo, args=(order.pk, items), daemon=True)

                order_in_silpo.delay(order.pk, items)
                # or
                # order_in_silpo.apply_async()
            case "kfc":
                #thread = Thread(target=order_in_kfc, args=(order.pk, items), daemon=True)
                order_in_kfc.delay(order.pk, items)
            case _:
                raise ValueError(
                    f"Restaurant {restaurant.name} is not available for processing"
                )
        # thread.start()
        # threads.append(thread)
