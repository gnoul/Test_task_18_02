import json
from django.apps import apps
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework import viewsets

from worker import celery
from orders.serializer import OrdersSerializer
while not settings.configured:
    pass
Orders = apps.get_model('orders', 'orders')


class OrdersViewSet(viewsets.ModelViewSet):

    queryset = Orders.objects.filter(syncstatus=3).order_by('id')
    serializer_class = OrdersSerializer


@csrf_exempt
def statushandler(request):
    if request.method == 'POST':
        task_name = f'{settings.SERVICE_NAME}.save_order'
        celery.send_task(task_name, args=[json.loads(request.body)])
    return HttpResponse("Ok {}".format(settings.SERVICE_NAME))


