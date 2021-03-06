# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-21 12:50
from __future__ import unicode_literals

from django.db import migrations
from django.contrib.auth.models import User


def addsuperuser(apps, schema_editor):
    user = User(pk=1, username="admin", is_active=True,
                is_superuser=True, is_staff=True,
                last_login="2017-09-01T13:20:30+03:00",
                email="email@email.com",
                date_joined="2017-09-01T13:20:30+03:00")
    user.set_password('admin')
    user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(addsuperuser),
    ]
