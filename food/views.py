import csv
import io
from datetime import date
from typing import Any

from rest_framework import  viewsets, serializers, routers, permissions
from rest_framework.decorators import action, permission_classes, api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError  # always returns status_code=400
from django.db import transaction
from django.shortcuts import redirect

from django.contrib.auth.decorators import login_required, user_passes_test

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.pagination import PageNumberPagination

from .models import Restaurant, Dish, Order, OrderItem, OrderStatus
from .enums import DeliveryProvider
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
    delivery_provider = serializers.CharField()

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


class BaseFilters:
    @staticmethod
    def snake_to_camel(value):
        parts = value.split("_")
        return parts[0] + "".join(word.capitalize() for word in parts[1:])

    @staticmethod
    def camel_to_snake_case(value):
        result = []
        for char in value:
            if char.isupper():
                if result:
                    result.append("_")
                result.append(char.lower())
            else:
                result.append(char)
        return "".join(result)

    def __init__(self, **kwargs):
        errors: dict[str, dict[str, Any]] = {"queryParams": {}}

        for key, value in kwargs.items():

            # filter shouldn't define extract methods for pagination query params
            if key in ['page', 'size', 'limit', 'offset']:
                continue

            _key = self.camel_to_snake_case(key)

            try:
                 extractor = getattr(self, f"extract_{_key}")
            except AttributeError as error:
                errors["queryParams"][key] = f"You forgot to define `extract_{_key}` method in  your {self.__class__.__name__} class"
                #raise ValidationError(f"You forgot to define `extract_{_key}` method") from error
                raise ValidationError(errors)
            try:
                _extracted_value = extractor(value)
            except ValidationError as error:
                errors["queryParams"][key] = str(error)
            else:
                setattr(self, _key, _extracted_value)
            if errors["queryParams"]:
                raise ValidationError(errors)

        # self.delivery_provider = self.extract_delivery_provider(kwargs.get("deliveryProvider"))
        # if "deliveryProvider" in kwargs:
        #     self.delivery_provider = kwargs.get("deliveryProvider")


class FoodFilters(BaseFilters):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # def __init__(self, **kwargs):
    #     self.delivery_provider = self.extract_delivery_provider(kwargs.get("deliveryProvider"))
    #     if "deliveryProvider" in kwargs:
    #         self.delivery_provider = kwargs.get("deliveryProvider")

    def extract_delivery_provider(self, provider: str | None) -> DeliveryProvider | None:
        if provider is None:
            return None
        else:
            provider_name = provider.upper()
            try:
                _provider = DeliveryProvider[provider_name]
            except KeyError:
                raise ValidationError(f"Provider {provider} is not supported")
            else:
                return _provider


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
        # restaurants = Restaurant.objects.all()
        # serializer = RestaurantSerializer(restaurants, many=True)
        # return Response(serializer.data)

        name: str | None = request.query_params.get("name")
        dishes = Dish.objects.all() if name is None else Dish.objects.filter(name__icontains=name)

        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(dishes, request, view=self)
        if page is not None:
            serializer = DishSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = DishSerializer(dishes, many=True)
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
        filters = FoodFilters(**request.query_params.dict())

        #status: str | None = request.query_params.get("status")
        #orders = Order.objects.all() if status is None else Order.objects.filter(status=status)

        orders = Order.objects.all() if not hasattr(filters, "delivery_provider") else Order.objects.filter(delivery_provider=filters.delivery_provider)

        # # Page Number Pagination
        # paginator = PageNumberPagination()
        # paginator.page_size = 2
        # page = paginator.paginate_queryset(orders, request, view=self)
        # if page is not None:
        #     serializer = OrderSerializer(page, many=True)
        #     return paginator.get_paginated_response(serializer.data)
        #
        # serializer = OrderSerializer(orders, many=True)
        # return Response(serializer.data)

        # # Limit Offset Paginator
        # next http://localhost:8000/food/orders/?limit=2&offset=2
        paginator = LimitOffsetPagination()
        page = paginator.paginate_queryset(orders, request, view=self)
        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)


        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


@login_required  #  uses Django’s session cookie (what browser sends after login)
def import_dishes(request):
    if request.method != "POST":
        raise ValueError(f"Method {request.method} is not allowed on this resource")

    if not request.user.role == Role.ADMIN:
        raise PermissionDenied("Only admins can import dishes.")

    csv_file = request.FILES.get("file")
    if csv_file is None:
        raise ValueError("No CSV File Provided")
    decoded = csv_file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    total = 0

    for row in reader:
        restaurant_name = row["restaurant"]
        try:
            rest = Restaurant.objects.get(name__icontains=restaurant_name.lower())
        except Restaurant.DoesNotExist:
            print(f"Skipping restaurant {restaurant_name}")
            continue
        else:
            print(f"Restaurant {rest} found")

        Dish.objects.create(name=row["name"], price=int(row["price"]), restaurant=rest)
        total += 1

    print(f"{total} dishes uploaded to the database")

    return redirect(request.META.get("HTTP_REFERER", "/"))


router = routers.DefaultRouter()
router.register(
    prefix="",
    viewset=FoodAPIViewSet,
    basename="food"
)