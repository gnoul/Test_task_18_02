import uuid
from django.db import models
from django.core.exceptions import ValidationError
from orders.const import *
from orders.tools import send_task


class Orders(models.Model):

    Status = (
        (ST_NEW, 'new'),
        (ST_UPD, 'updated'),
        (ST_OK, 'ok'),
        (ST_DEL, 'mark to del'),
        (ST_DEL_SYNCED, 'deleted'),
        (ST_COLLISION, 'collision'),
        (ST_ERROR, 'error'),
        (ST_ERROR_SYNCED, 'error synced'),
    )

    data1 = models.TextField()
    data2 = models.TextField()
    data3 = models.TextField()
    valid = models.BooleanField(default=False, editable=False)
    datechange = models.DateTimeField(auto_now=True)
    datesync = models.DateTimeField(auto_now_add=True, editable=False)
    syncstatus = models.IntegerField(choices=Status, default=ST_NEW)
    version = models.PositiveIntegerField(default=1)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)

    def __init__(self, *args, **kwargs):
        super(Orders, self).__init__(*args, **kwargs)
        self.old_data = (self.data1, self.data2, self.data3)
        self.old_status = self.syncstatus

    def __str__(self):
        return 'Order: {}, data {}'.format(self.id, [self.data1, self.data2, self.data3])

    def save(self, *args, **kwargs):
        send = True if not self.pk and self.syncstatus == ST_NEW or self.syncstatus in [ST_DEL, ST_ERROR] else False
        # При изменении данных проверяем синхронизирован ли объект
        if self.old_data != (self.data1, self.data2, self.data3):
            if self.syncstatus == ST_OK:
                # Данные изменились. Запускаем синхронизацию
                self.syncstatus = ST_UPD
                self.version += 1
                send = True
            elif self.syncstatus == ST_SYNC:
                self.syncstatus = ST_OK
                send = True
            else:
                # Объект не синхронизирован или его нельзя обновлять
                raise ValidationError('Object is locked')
        self.valid = True if self.syncstatus == ST_OK else False

        super(Orders, self).save(*args, **kwargs)
        if send:
            send_task(self)
            
    def delete(self, *args):
        self.syncstatus = ST_DEL
        self.save()
