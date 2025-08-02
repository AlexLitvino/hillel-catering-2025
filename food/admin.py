from django.contrib import admin

from .models import Dish, Order, OrderItem, Restaurant

#admin.site.register(Restaurant)
admin.site.register(OrderItem)


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "restaurant", "id")
    search_fields = ("name",)
    list_filter = ("name", "restaurant")
    # actions = ("import_csv",)


class DishOrderItemInline(admin.TabularInline):
    model = OrderItem


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "delivery_provider", "id")
    inlines = (DishOrderItemInline,)

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "id")