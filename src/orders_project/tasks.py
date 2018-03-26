import os
from os import environ as env
import requests
import django
from worker import celery
from orders.const import *
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()
from orders.models import Orders
from orders.tools import send_task

SERVICE_NAME = env.get('SERVICE_NAME')
SECOND_SERVICE = env.get('SECOND_SERVICE')
celery.config_from_object('django.conf:settings', namespace='CELERY')


@celery.task(name=f'{SERVICE_NAME}.process_status')
def send_update(params, url):
    try:
        requests.post(url, json=params)
    except requests.RequestException:
        pass
    return params


@celery.task(name=f'{SERVICE_NAME}.save_order')
def save_order(data):
    status = data.get('syncstatus')
    uuid = data.get('uuid')
    qs = Orders.objects.filter(uuid=uuid)
    if not qs:
        order = Orders(data1=data.get('data1'), data2=data.get('data2'), data3=data.get('data3'),
                       uuid=uuid, valid=False)
        if status == 1:
            # Получаем ноывый объект с другого сервиса
            order.syncstatus = 3
    else:
        sdict = {  # Таблица установки нового статуса в зависимости от статусов синхронизируемых объектов
            ST_NEW: {ST_NEW: ST_COLLISION, ST_OK: ST_OK, ST_COLLISION: ST_COLLISION},
            ST_UPD: {ST_UPD: ST_COLLISION, ST_OK: ST_SYNC, ST_COLLISION: ST_COLLISION, ST_DEL: ST_COLLISION},
            ST_OK: {ST_NEW: ST_OK, ST_UPD: ST_OK},
            ST_DEL: {ST_UPD: ST_COLLISION, ST_OK: ST_DEL_SYNCED, ST_DEL: ST_COLLISION,
                     ST_DEL_SYNCED: ST_DEL_SYNCED,  ST_COLLISION: ST_COLLISION},
            ST_DEL_SYNCED: {ST_DEL: ST_DEL_SYNCED},
            ST_COLLISION: {ST_NEW: ST_COLLISION, ST_UPD: ST_COLLISION, ST_DEL: ST_COLLISION,
                           ST_COLLISION: ST_COLLISION},
            ST_ERROR_SYNCED: {ST_ERROR: ST_ERROR_SYNCED},
        }
        order = qs[0]
        # Если пришли изменения и объект не заблокирован, обновляем данные
        if status == ST_OK and order.syncstatus == ST_SYNC:
            order.data1 = data.get('data1')
            order.data2 = data.get('data2')
            order.data3 = data.get('data3')
            order.version = data.get('version')
        # Обновляем статус объекта
        if status in sdict and order.syncstatus in sdict[status]:
            order.syncstatus = sdict[status][order.syncstatus]
        else:
            if order.syncstatus == ST_ERROR:
                order.syncstatus = ST_ERROR_SYNCED
            elif order.syncstatus == ST_ERROR_SYNCED:
                pass
            else:
                order.syncstatus = ST_ERROR

        # Если пришли изменения и объект не заблокирован, обновляем данные
        if order.old_status == ST_OK and order.syncstatus == ST_SYNC:
            order.data1 = data.get('data1')
            order.data2 = data.get('data2')
            order.data3 = data.get('data3')
            order.version = data.get('version')
    order.valid = True if order.syncstatus == ST_OK else False
    print()
    order.save()
    if status != order.syncstatus and order.syncstatus != ST_SYNC:
        send_task(order)
