from datetime import date

from rest_framework import  viewsets, serializers, routers, permissions
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError  # always returns status_code=400
from django.db import transaction

from .models import Restaurant, Dish, Order, OrderItem, OrderStatus
from users.models import User, Role

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
    id = serializers.PrimaryKeyRelatedField(read_only=True)
    items = OrderItemSerializer(many=True)
    eta = serializers.DateField()
    total = serializers.IntegerField(min_value=1, read_only=True)
    status = serializers.ChoiceField(OrderStatus.choices(), read_only=True)

    @property
    def calculated_total(self) -> int:
        total = 0
        for item in self.validated_data["items"]:
            dish: Dish = item["dish"]
            quantity: int = item["quantity"]
            total += dish.price * quantity

        return total

    # def validate_<any_filed_name>
    def validate_eta(self, value: date):
        if (value - date.today()).days < 1:
            raise ValidationError("ETA must be min 1 day after today")
        else:
            return value


class IsAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        assert type(request.user) == User
        user: User = request.user

        if user.role == Role.ADMIN:
            return True
        else:
            return False


class FoodAPIViewSet(viewsets.GenericViewSet):

    def get_permissions(self):
        match self.action:
            case "all_orders" | "create_dish":
                return [permissions.IsAuthenticated(), IsAdmin()]
            case _:
                return [permissions.IsAuthenticated()]


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


    @action(methods=["post"], detail=False, url_path=r"create-dishes")
    def create_dish(self, request: Request):
        """
        {
            "name": "Salad",
            "price": 23,
            "restaurant": 1
        }
        """
        serializer = DishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # as "restaurant" is excluded from DishSerializer it should be passed manually
        restaurant_id = request.data.get("restaurant")
        restaurant = Restaurant.objects.get(id=restaurant_id)

        dish = serializer.save(restaurant=restaurant)

        return Response(DishSerializer(dish).data, status=201)


    # HTTP POST food/orders
    # I renamed url_path for this method to create-orders as it stops working
    # ChatGPT states that we could have only one method with unique url_path and need to dispatch GET/POST inside method
    # or rename url_path
    @transaction.atomic
    @action(methods=["post"], detail=False, url_path=r"create-orders")
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
            eta=serializer.validated_data["eta"],
            total=serializer.calculated_total
        )

        items = serializer.validated_data["items"]

        for dish_order in items:
            instance = OrderItem.objects.create(
                dish=dish_order["dish"],
                quantity=dish_order["quantity"],
                order=order
            )
            print(f"New dish order item is created: {instance.pk}")

        print(f"New food order is created: {order.pk}. ETA: {order.eta}")

        # TODO: run scheduler

        return Response(
        #     data={
        #     "id": order.pk,
        #     "status": order.status,
        #     "eta": order.eta,
        #     "total": order.total
        # }   # OR
            OrderSerializer(order).data
            , status=201)


    # HTTP GET /food/orders/4
    @action(methods=["get"], detail=False, url_path=r"orders/(?P<id>\d+)")
    def retrieve_order(self, request: Request, id: int) -> Response:
        order = Order.objects.get(id=id)
        serializer = OrderSerializer(order)
        return Response(data=serializer.data)


    @action(methods=["get"], detail=False, url_path=r"orders")  # , name="orders_list" ???
    def all_orders(self, request):
        orders = Order.objects.all()

        serializer = OrderSerializer(orders, many=True)

        return Response(serializer.data)



router = routers.DefaultRouter()
router.register(
    prefix="",
    viewset=FoodAPIViewSet,
    basename="food"
)