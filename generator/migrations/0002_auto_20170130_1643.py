# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2017-01-30 18:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('generator', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExecutionLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='generator.ReportTypes')),
            ],
        ),
        migrations.RemoveField(
            model_name='executiondashboard',
            name='data_ult_execucao',
        ),
        migrations.RemoveField(
            model_name='executiondashboard',
            name='tempo_execucao',
        ),
    ]