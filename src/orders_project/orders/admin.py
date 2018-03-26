from django.contrib import admin
from orders.models import Orders


@admin.register(Orders)
class OrdersAdmin(admin.ModelAdmin):
    pass
