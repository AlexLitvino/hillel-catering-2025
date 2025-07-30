from django.shortcuts import render
from rest_framework import  viewsets, serializers, routers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Restaurant, Dish, Order, OrderItem, OrderStatus
from users.models import User

class DishSerializer(serializers.ModelSerializer):

    class Meta:
        model = Dish
        exclude = ["restaurant"]  # exclude the same field from nested JSON


class RestaurantSerializer(serializers.ModelSerializer):

    # nested serializer
    dishes = DishSerializer(many=True)

    class Meta:
        model = Restaurant
        fields = "__all__"  # to not specify all fields


class OrderItemSerializer(serializers.Serializer):
    dish = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all())
    quantity = serializers.IntegerField(min_value=1, max_value=20)


class OrderSerializer(serializers.Serializer):
    items = OrderItemSerializer(many=True)
    eta = serializers.DateField()
    total = serializers.IntegerField(min_value=1, read_only=True)
    status = serializers.ChoiseField(OrderStatus.choices(), read_only=True)


class FoodAPIViewSet(viewsets.GenericViewSet):

    @action(methods=["get"], detail=False) # if True, primary key is expected in router
    def dishes(self, request: Request):
        """
        [
            {
                id: 1,
                name: Bueno,
                dishes: [
                    {
                        id: 21,
                        name: Kola,
                        price: 32
                    },
                ]
            }
        ]
        """
        restaurants = Restaurant.objects.all()
        serializer = RestaurantSerializer(restaurants, many=True)
        return Response(serializer.data)

    # HTTP POST food/orders
    @action(methods=["post"], detail=False, url_path=r"orders")
    def create_order(self, request: Request):
        """
        >>> HTTP Request
            "items": [
                {
                    "dish": 3, # id
                    "quantity": 2
                }
            ],
            "eta": "2025-07-14"

        <<< HTTP Response
            "items": [
                {
                    "dish": 3, # id
                    "quantity": 2
                }
            ],
            "eta": "2025-07-14",
            "id": 10,
            "status": "not_started"
        """
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = request.user
        assert type(request.user) is User

        order = Order.objects.create(
            status=OrderStatus.NOT_STARTED,
            user=user,
            delivery_provider="uklon",
            eta=serializer.validated_data("eta")
        )

        items = serializer.validated_data("items")

        for dish_order in items:
            instance = OrderItem.objects.create(
                dish=dish_order("dish"),
                quantity=dish_order("quantity"),
                order=order
            )
            print(f"New dish order item is created: {instance.pk}")

        print(f"New food order is created: {order.pk}. ETA: {order.eta}")

        # TODO: run scheduler

        return Response(data={
            "id": order.pk,
            "status": order.status,
            "eta": order.eta,
            "total": order.total
        }, status=201)


    # HTTP GET /food/orders/4
    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)
        serializer = OrderSerializer(order)
        return Response(data=serializer.data)


router = routers.DefaultRouter()
router.register(
    prefix="",
    viewset=FoodAPIViewSet,
    basename="food"
)