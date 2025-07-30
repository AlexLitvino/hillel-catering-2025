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


## pipenv commands
pipenv shell
pipenv graph
pipenv lock
pipenv sync
