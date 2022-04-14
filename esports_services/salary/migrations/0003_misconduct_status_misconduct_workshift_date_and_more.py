# Generated by Django 4.0.3 on 2022-04-14 17:29

import datetime
from django.db import migrations, models
from django.utils.timezone import utc

from salary.models import Misconduct


class Migration(migrations.Migration):

    dependencies = [
        ('salary', '0002_remove_workingshift_comment_and_more'),
    ]

    def set_workshift_date(*args):
        for misconduct in Misconduct.objects.all():
            misconduct.workshift_date = misconduct.misconduct_date
            misconduct.save()

    operations = [
        migrations.AddField(
            model_name='misconduct',
            name='status',
            field=models.CharField(choices=[('AD', 'Ожидает объяснение'), ('WT', 'Ожидает решение'), ('CL', 'Решение принято')], default='AD', max_length=60, verbose_name='Статус рассмотрения'),
        ),
        migrations.AddField(
            model_name='misconduct',
            name='workshift_date',
            field=models.DateField(default=datetime.datetime(2022, 4, 14, 17, 29, 59, 216923, tzinfo=utc), verbose_name='Дата смены'),
            preserve_default=False,
        ),
        migrations.RunPython(set_workshift_date),
        migrations.AlterField(
            model_name='misconduct',
            name='misconduct_date',
            field=models.DateField(verbose_name='Дата нарушения'),
        ),
    ]
