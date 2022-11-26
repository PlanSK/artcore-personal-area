# Generated by Django 4.1 on 2022-11-26 13:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salary', '0002_alter_position_position_salary'),
    ]

    operations = [
        migrations.RenameField(
            model_name='workingshift',
            old_name='vr_revenue',
            new_name='additional_services_revenue'
        ),
        migrations.AlterField(
            model_name='workingshift',
            name='additional_services_revenue',
            field=models.FloatField(verbose_name='Выручка доп. услуги', default=0.0)
        ),
    ]
