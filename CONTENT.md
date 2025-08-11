# Lesson 16 (t=5162) Project start

 django-admin startproject config . 
 python .\manage.py
 python .\manage.py runserver
  http://127.0.0.1:8000/
 
python .\manage.py migrate

python .\manage.py createsuperuser

Table Plus - Graphical Client for DBs


# Lesson 18 (t=1952)
python .\manage.py startapp users   # create new sub-app to work with users
Goto users/models.py and create class User by overriding django user
https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#substituting-a-custom-user-model
https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-AUTH_USER_MODEL
```python
class User(AbstractBaseUser, PermissionMixin):
    pass
```

Fields types
https://docs.djangoproject.com/en/5.2/ref/models/fields/#django.db.models.CharField

To use it instead of built-in, in settings.py add
```python
AUTH_USER_MODEL = "users.User"
```

Go to settings.py and add to INSTALLED_APPS
"users"
OR
"users.apps.UsersConfig"

python manage.py makemigrations

TODO:Why delete db???
python manage.py migrate users  # users - you could specify app this migration is applied to
django.db.migrations.exceptions.InconsistentMigrationHistory: Migration admin.0001_initial is applied before its dependency users.0001_initial on database 'default'.
Need to remove db

email - is selected is main field for login

 python .\manage.py createsuperuser
 Error: AttributeError: 'Manager' object has no attribute 'get_by_natural_key'
 Because overides User class, so need to define manager to work with this model
 
Manager - objects:
User.objects.all()
User.objects.create()
User.objects.filter()
User.objects.get()
User.objects.delete()
User.objects.filter(name__in=['John', 'Mary', 'Karl']).delete()


Add class 
```python
class UserManager(BaseUserManager):
    pass
```
 python .\manage.py createsuperuser
Error: AttributeError: 'UserManager' object has no attribute 'create_superuser'

For class UserManager need to define methods: create_user and create_superuser

python .\manage.py createsuperuser - now command works

But password is not hashed
Adding password hashing, re-create db


## Authentication
https://django-rest-framework-simplejwt.readthedocs.io/en/latest/getting_started.html
In INSTALLED_APPS add "rest_framework"

In settings.py add
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication'
    ]
}
```
Add SIMPLE_JWT settings to settings.py

To urls.py add
```python
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

path('auth/token/', TokenObtainPairView.as_view(), name='obtain_token')
```


## Adding UsersAPIViewSet 
In urls.py add
```python
from users.views import UsersAPIViewSet

path('users/', UsersAPIViewSet.as_view())
```

TODO:...



## Register User model in admin panel
In admin.py
```python
from django.contrib import admin

# Register your models here.
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass
```

https://docs.djangoproject.com/en/5.2/topics/class-based-views/
https://www.django-rest-framework.org/tutorial/3-class-based-views/


# Lesson 19
python manage.py startapp food
To settings.py add "food" to INSTALLED_APPS

In models.py add, but move it to specific module enums.py:
(First of all describe existing states)
```python
import enum

class OrderStatus(enum.StrEnum):
    NOT_STARTED = enum.auto()
    COOKING_REJECTED = enum.auto()
    COOKING = enum.auto()
    COOKED = enum.auto()
    DELIVERY_LOOKUP = enum.auto()
    DELIVERY = enum.auto()
    DELIVERED = enum.auto()
    NOT_DELIVERED = enum.auto()
    CANCELLED_BY_CUSTOMER = enum.auto()
    CANCELLED_BY_MANAGER = enum.auto()
    CANCELLED_BY_ADMIN = enum.auto()
    CANCELLED_BY_RESTAURANT = enum.auto()
    CANCELLED_BY_DRIVER = enum.auto()
    FAILED = enum.auto()
```

In models.py add models for Restaurant, Dish, Order and OrderItem:
```python

```
Foreign key is suggested to specify not as class - Restaurant, but as string "Restaurant"
In CharField you could specify choices - it would be dropdown in admin panel. It should be collection of collection. For this, adding method choices to enums.Order

Provider could be kept as Order in code or in DB. It depends whether you will change providers during app work. Keeping provider in code - faster.
If keep in code - use CHarField, if in separate DB table - use Foreign key - for this, before food app create Logistic app to define providers.

In Order, user field is foreign key but it is specified via settings.py: settings.AUTH|_USER_MODEL

CASCADE update usually is not used. More often data sets to null.

Make migrations:
manage.py makemigrations food
manage.py migrate

Register food models for admin
t=3442
```python
admin.site.register(Restaurant)
admin.site.register(OrderItem)


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "restaurant")
    search_fields = ("name",)
    list_filter = ("name", "restaurant")
    # actions = ("import_csv",)
```

Override __str__ in model to make view in admin panel.
ANOTHER way to display is to define list_display = ("id", "name") - columns you want to see - in ***Admin class.
First element is a link, so id could be moved to the end and at the beginning have name for convenience.

search_fields = ("name",) - to add search
list_filter = ("name",) - filters

Tabular inline???
```python
class DishOrderItemInline(admin.TabularInline):
    model = OrderItem
```

## User

Advanced REST Client 

APIViewSet create() method - validate, save to DB and return data
ModelSerializer works same as ModelAdmin

AUTH_PASSWORD_VALIDATORS - restrictions for password, in settings.py

Password should be hashed before saving


python manage.py shell


permission_classes - functions that returns boolean value

Access matrix = Role X Endpoint
Approach: Close everything and open if needed
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
}
```


## Filtering
Using GET or POST method? Depending on length of request

django-filters?

Set default filter backend in settings.py
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']
}

request.query_params
request.query_params.get("status")

Filtering by query_params:
```python
    @action(methods=["get"], detail=False, url_path=r"orders")  # , name="orders_list" ???
    def all_orders(self, request):
        status: str | None = request.query_params.get("status")

        orders = Order.objects.all() if status is None else Order.objects.filter(status=status)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
```

Using built-in search_fields is not very good as it performs search by all columns that slow down search
https://www.django-rest-framework.org/api-guide/filtering/#searchfilter


## Pagination
https://www.django-rest-framework.org/api-guide/pagination/

It enables pagination for all ListViewSet
```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100
}
```

### PageNumberPagination - page1, page2, ...
```python
        paginator = PageNumberPagination()
        paginator.page_size = 2
        page = paginator.paginate_queryset(orders, request, view=self)
        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
```

### LimitOffsetPagination - show more pagination
Problem with removing elements - some data could be not shown


## DB snapshot
Use it to load test data into DB. Keep in /fixture directory 
python manage.py dumpdata --natural-primary --natural-foreign --indent 2 > /tmp/dump.json
python manage.py loaddata /tmp/dump.json


## Importing dishes.csv
Create templates/admin/dish/change_list.html
In settings.py
```python
TEMPLATES = [
    {
        "DIRS": [BASE_DIR / "templates"],
    }
```
Need to inherit:
{% extends "admin/change_list.html" %}

To get files input should have name attribute and enctype="multipart/form-data" 
<form action="import-dishes/" method="POST" enctype="multipart/form-data">
<input type="file" name="file" accept="csv" />

Return to where started
return redirect(request.META.get("HTTP_REFERER", "/"))

For case insensitive:
rest = Restaurant.objects.get(name__icontains=restaurant_name.lower())


## Caching
https://docs.djangoproject.com/en/5.2/topics/cache/
https://www.django-rest-framework.org/api-guide/caching/


Endpoint caching
### cache_page
https://docs.djangoproject.com/en/dev/topics/cache/#django.views.decorators.cache.cache_page
from django.views.decorators.cache import cache_page

@cache_page(10) # cached for 10 seconds
def dishes

This will fail because @cache_page could be applied only to functions:

from django.utils.decorators import method decorator
@method_decorator(cache_page(10)) # cached for 10 seconds
def dishes

Check response time in Postman


Django cache settings:
https://docs.djangoproject.com/en/5.2/ref/settings/#caches

### Redis
https://redis.readthedocs.io/en/latest/
https://redis.readthedocs.io/en/latest/commands.html#redis.commands.cluster.RedisClusterCommands.delete

redis-cli  - to start CLI
```shell
root@c8a4bd9ab346:/data# redis-cli
127.0.0.1:6379> set name John
OK
127.0.0.1:6379> get name
"John"
127.0.0.1:6379> get name2
(nil)
127.0.0.1:6379>
```

Cache should be used on idempotent methods
Cache better use not in view but in Services that could be used by views.

Sending email
https://docs.djangoproject.com/en/5.2/topics/email/

Email backends
https://docs.djangoproject.com/en/5.2/topics/email/#topic-email-backends

For user activation link, link to frontend should be specified

pipenv install redis

Mailhog - to test emails
Mailpit - newer service to test emails (Web + SMTP)


## Dockerization
WORKDIR /app - created automatically

ENV PYTHONDONTWRITEBYTECODE=1 - not create pycache directory

docker build -t catering-api
docker run --rm -p 8000:8000 catering-api
docker run --rm -p 8000:8000 -e DJANGO_SECRET_KEY="..." catering-api
docker run --rm -p 8000:8000 -e DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}  -e DJANGO_DEBUG=${DJANGO_DEBUG} catering-api

make <STAGE>  (make build, make docker)

source .env

Docker secrets
https://docs.docker.com/build/building/secrets/

docker compose build
docker compose up
docker compose down
docker compose logs <SERVICE_NAME>
docker compose restart <SERVICE_NAME>
docker compose exec <SERVICE_NAME> <COMMAND>

Docker compose restart policy
https://docs.docker.com/engine/containers/start-containers-automatically/

docker compose exec api bash
docker compose exec api python manage.py migrate
docker compose exec database psql -U postgres 
\l
\c catering
\dt
docker compose exec api python manage.py createsuperuser



nixOS
Istio
Long Polling


## pipenv commands
pipenv shell
pipenv graph
pipenv lock
pipenv sync
