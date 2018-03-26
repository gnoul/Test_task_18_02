from django.apps import apps
from rest_framework import serializers

Orders = apps.get_model('orders', 'orders')


class OrdersSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Orders
        fields = ['data1', 'data2', 'data3']


