# import time
from django.conf import settings
from worker import celery
from rest_framework import serializers


class OrdersStatusSerializer(serializers.Serializer):
    data1 = serializers.CharField()
    data2 = serializers.CharField()
    data3 = serializers.CharField()
    valid = serializers.BooleanField()
    datechange = serializers.DateTimeField()
    datesync = serializers.DateTimeField()
    syncstatus = serializers.IntegerField()
    version = serializers.IntegerField()
    uuid = serializers.UUIDField()


def send_task(self):
    # time.sleep(2)
    url = f'http://{settings.SECOND_SERVICE}/update'
    task_name = f'{settings.SERVICE_NAME}.process_status'
    ser = OrdersStatusSerializer(self)
    celery.send_task(task_name, args=[ser.data, url])
