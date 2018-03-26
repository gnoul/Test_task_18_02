from django.test import TestCase
from os import environ as env
from uuid import uuid4
from unittest import mock
from django.core.exceptions import ValidationError
from orders.const import *
from orders.models import Orders
from orders.tools import OrdersStatusSerializer
from tasks import save_order, send_update

POSTGRES_USER = env.get('POSTGRES_USER', 'pguser1')
POSTGRES_DB = env.get('POSTGRES_DB', 'pddb1')
POSTGRES_PASSWORD = env.get('POSTGRES_PASSWORD', 'ohd7ua2Quu')
POSTGRES_HOST = env.get('POSTGRES_HOST', 'db')
POSTGRES_PORT = env.get('POSTGRES_PORT', 5432)


class TestRequestsCall(TestCase):

    def setUp(self):
        super().setUpClass()
        for i in range(10):
            status = ST_NEW if i > 3 else ST_OK
            Orders.objects.create(data1=f'{i}data1', data2=f'{i}1data2', data3=f'{i}1data3', syncstatus=status)

    def test_new(self):
        on = Orders.objects.create(data1='1data1', data2='1data2', data3='1data3')
        ot = Orders.objects.get(uuid=on.uuid)
        # Создание
        self.assertTrue(on.uuid == ot.uuid)
        self.assertTrue(ot.syncstatus == ST_NEW)
        self.assertTrue(on.data1 == ot.data1)
        self.assertTrue(on.data2 == ot.data2)
        self.assertTrue(on.data3 == ot.data3)

        # Получение синхронизации
        params_local = OrdersStatusSerializer(ot).data
        params_local['syncstatus'] = ST_OK
        save_order(params_local)
        ou = Orders.objects.get(pk=on.pk)
        self.assertTrue(ou.syncstatus == ST_OK)

    def test_new_remote(self):
        # Получение нового объекта с удаленного сервиса
        ot = Orders.objects.create(data1='1data1', data2='1data2', data3='1data3')
        self.assertTrue(ot.version == ST_NEW)
        params = OrdersStatusSerializer(ot).data
        uuid = uuid4()
        params['uuid'] = uuid
        save_order(params)
        oy = Orders.objects.filter(uuid=uuid).first()
        self.assertTrue(oy.syncstatus == ST_OK)

    def test_upd_local(self):
        # Локальное изменение и синхронизация объекта
        ot = Orders.objects.filter(syncstatus=ST_OK).first()
        self.assertTrue(ot.valid)
        version = ot.version
        ot.data1 = 'Test UPD 1 String'
        ot.save()
        self.assertTrue(ot.syncstatus == ST_UPD)

        # Проверяем как изменился параметр valid
        oy = Orders.objects.get(pk=ot.pk)
        self.assertFalse(oy.valid)

        params_local = OrdersStatusSerializer(ot).data
        params_local['syncstatus'] = ST_OK
        save_order(params_local)
        ou = Orders.objects.get(pk=ot.pk)
        self.assertTrue(ou.syncstatus == ST_OK)
        self.assertTrue(ou.version == version + 1)

    def test_upd_remote(self):
        # Удаленное создание и синхронизация объекта
        # Имитируем удаленное изменение изменив один объект
        # и заменив ему ключевой параметр uuid от другого активного объекта
        ot = Orders.objects.filter(syncstatus=ST_OK).first()
        ot.data1 = 'Test UPD 2 String'
        ot.save()
        self.assertTrue(ot.syncstatus == ST_UPD)
        params_remote = OrdersStatusSerializer(ot).data

        # Объект ot не попадется. У него уже другой статус
        oy = Orders.objects.filter(syncstatus=3).first()
        params_remote['uuid'] = oy.uuid
        save_order(params_remote)
        ou = Orders.objects.get(pk=oy.pk)
        self.assertTrue(ou.syncstatus == ST_OK)
        self.assertTrue(ou.data1 == ot.data1)
        self.assertTrue(ou.data2 == ot.data2)
        self.assertTrue(ou.data3 == ot.data3)
        self.assertTrue(ou.valid)

    def test_del_remote(self):
        ot = Orders.objects.filter(syncstatus=ST_OK).first()
        ot.delete()
        ox = Orders.objects.get(pk=ot.pk)
        self.assertTrue(ox.syncstatus == ST_DEL)

        oy = Orders.objects.filter(syncstatus=ST_OK).first()
        params = OrdersStatusSerializer(ox).data
        params['uuid'] = oy.uuid
        save_order(params)
        oz = Orders.objects.get(pk=oy.pk)
        self.assertTrue(oz.syncstatus == ST_DEL_SYNCED)

    def test_del_local(self):
        ot = Orders.objects.filter(syncstatus=ST_OK).first()
        params = OrdersStatusSerializer(ot).data
        params['syncstatus'] = ST_DEL
        save_order(params)
        oz = Orders.objects.get(pk=ot.pk)
        self.assertTrue(oz.syncstatus == ST_DEL_SYNCED)

    def test_collision(self):
        # Collizion Upd/Upd
        oy = Orders.objects.filter(syncstatus=3).first()
        oy.data1 = 'Test String'
        oy.save()
        params = OrdersStatusSerializer(oy).data
        save_order(params)
        oy = Orders.objects.get(pk=oy.pk)
        self.assertTrue(oy.syncstatus == ST_COLLISION)

        # Collizion Del/Upd
        oy = Orders.objects.filter(syncstatus=3).first()
        oy.delete()
        params = OrdersStatusSerializer(oy).data
        params['syncstatus'] = ST_UPD
        save_order(params)
        oy = Orders.objects.get(pk=oy.pk)
        self.assertTrue(oy.syncstatus == ST_COLLISION)

        # Collizion Del/Del
        oy = Orders.objects.filter(syncstatus=3).first()
        oy.delete()
        params = OrdersStatusSerializer(oy).data
        save_order(params)
        oy = Orders.objects.get(pk=oy.pk)
        self.assertTrue(oy.syncstatus == ST_COLLISION)

    def test_error_sync(self):
        ot = Orders.objects.filter(syncstatus=ST_OK).first()
        params = OrdersStatusSerializer(ot).data
        params['syncstatus'] = ST_ERROR
        save_order(params)
        ov = Orders.objects.get(pk=ot.pk)
        # self.assertTrue(ov.syncstatus == ST_ERROR_SYNCED)

        ox = Orders.objects.filter(syncstatus=ST_OK).first()
        ox.syncstatus = ST_ERROR
        ox.save()
        params = OrdersStatusSerializer(ox).data
        params['syncstatus'] = ST_ERROR_SYNCED
        save_order(params)
        oz = Orders.objects.get(pk=ox.pk)
        self.assertTrue(oz.syncstatus == ST_ERROR_SYNCED)


    def test_error_call(self):
        ot = Orders.objects.filter(syncstatus=ST_OK).first()
        ot.syncstatus = ST_UPD
        ot.save()
        params = OrdersStatusSerializer(ot).data
        params['syncstatus'] = ST_NEW
        save_order(params)
        ov = Orders.objects.get(pk=ot.pk)
        self.assertTrue(ov.syncstatus == ST_ERROR)
        # ot.syncstatus = ST_ERROR
        # ot.save()
        # ov = Orders.objects.get(pk=ot.pk)

    def test_lock(self):
        ot = Orders.objects.filter(syncstatus=ST_OK).first()
        ot.data1 = 'Test lock'
        ot.save()
        self.assertTrue(ot.syncstatus == ST_UPD)
        oz = Orders.objects.get(pk=ot.pk)
        oz.data2 = 'Test locck2'
        self.assertRaises(ValidationError, oz.save)
        self.assertRaisesMessage(ValidationError, 'Object is locked', oz.save)

    def test_object_live_cicle(self):
        # Creating
        # Service 1
        data1 = 'Object'
        data2 = 'LiFE'
        data3 = 'Cycle'
        data1_u = 'UPD1'
        data2_u = 'UPD2'
        data3_u = 'UPD3'
        o11 = Orders.objects.create(data1=data1, data2=data2, data3=data3)
        pk1 = o11.pk
        o12 = Orders.objects.get(pk=pk1)
        self.assertTrue(o12.syncstatus == ST_NEW)
        uuid_1 = o11.uuid
        # Service 2
        uuid_2 = uuid4()
        params1 = OrdersStatusSerializer(o11).data
        params1['uuid'] = uuid_2
        save_order(params1)
        o21 = Orders.objects.get(uuid=uuid_2)
        pk2 = o21.pk
        self.assertTrue(o21.syncstatus == ST_OK)
        # Service 1
        params2 = OrdersStatusSerializer(o21).data
        params2['uuid'] = uuid_1
        save_order(params2)
        o13 = Orders.objects.get(pk=pk1)
        self.assertTrue(o13.syncstatus == ST_OK)
        self.assertTrue(o13.data1 == data1)
        self.assertTrue(o13.data2 == data2)
        self.assertTrue(o13.data3 == data3)

        # Updating
        # Service 1
        o13.data1=data1_u
        o13.data2=data2_u
        o13.data3=data3_u
        o13.save()
        self.assertTrue(o13.syncstatus == ST_UPD)
        # Service 2
        params4 = OrdersStatusSerializer(o13).data
        params4['uuid'] = uuid_2
        save_order(params4)
        o22 = Orders.objects.get(pk=pk2)
        self.assertTrue(o22.syncstatus == ST_OK)
        self.assertTrue(o22.data1 == data1_u)
        self.assertTrue(o22.data2 == data2_u)
        self.assertTrue(o22.data3 == data3_u)
        # Service 1
        params5 = OrdersStatusSerializer(o22).data
        params5['uuid'] = uuid_1
        save_order(params5)
        o14 = Orders.objects.get(pk=pk1)
        self.assertTrue(o14.syncstatus == ST_OK)
        self.assertTrue(o14.data1 == data1_u)
        self.assertTrue(o14.data2 == data2_u)
        self.assertTrue(o14.data3 == data3_u)

        # Deleting
        # Service 2
        o22.delete()
        o23 = Orders.objects.get(pk=pk2)
        self.assertTrue(o23.syncstatus == ST_DEL)
        params6 = OrdersStatusSerializer(o23).data
        # Service 1
        params6['uuid'] = uuid_1
        save_order(params6)
        o15 = Orders.objects.get(pk=pk1)
        self.assertTrue(o15.syncstatus == ST_DEL_SYNCED)
        # Service 2
        params7 = OrdersStatusSerializer(o15).data
        params7['uuid'] = uuid_2
        save_order(params7)
        o24 = Orders.objects.get(pk=pk2)
        self.assertTrue(o24.syncstatus == ST_DEL_SYNCED)
        self.assertTrue(o24.data1 == data1_u)
        self.assertTrue(o24.data2 == data2_u)
        self.assertTrue(o24.data3 == data3_u)









