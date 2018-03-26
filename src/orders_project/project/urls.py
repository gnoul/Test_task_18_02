from django.conf.urls import url, include
from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt
from rest_framework import routers


from orders.views import OrdersViewSet, statushandler

router = routers.DefaultRouter()
router.register(r'orders', OrdersViewSet)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'update', csrf_exempt(statushandler)),
    url(r'^', include(router.urls))
]