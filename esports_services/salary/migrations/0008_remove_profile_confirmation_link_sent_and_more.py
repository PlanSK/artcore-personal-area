# Generated by Django 4.0.4 on 2022-05-27 18:17

from django.db import migrations, models, connection
from salary.models import *


class Migration(migrations.Migration):

    dependencies = [
        ('salary', '0007_profile_confirmation_link_sent'),
    ]

    def setting_statuses(*args):
        cursor = connection.cursor()
        for current_profile in Profile.objects.all():
            cursor.execute('SELECT email_is_confirmed, confirmation_link_sent FROM salary_profile WHERE user_id = %s', [current_profile.user_id])
            result = cursor.fetchone()

            if result[0]:
                current_profile.email_status = Profile.EmailStatus.CONFIRMED
            elif result[1]:
                current_profile.email_status = Profile.EmailStatus.SENT
            else:
                current_profile.email_status = Profile.EmailStatus.ADDED

            if current_profile.dismiss_date:
                current_profile.profile_status = Profile.ProfileStatus.DISMISSED
            else:
                current_profile.profile_status = Profile.ProfileStatus.ACTIVATED

            current_profile.save()

    operations = [
        migrations.AddField(
            model_name='profile',
            name='email_status',
            field=models.CharField(choices=[('ADD', 'Не подтвержден'), ('SNT', 'Ссылка направлена'), ('CNF', 'Подтвержден')], default='ADD', max_length=10, verbose_name='Состояние электронной почты'),
        ),
        migrations.AddField(
            model_name='profile',
            name='profile_status',
            field=models.CharField(choices=[('RG', 'Ожидает проверки'), ('WT', 'Ожидает активации'), ('ACT', 'Активирован'), ('DSM', 'Уволен')], default='RG', max_length=10, verbose_name='Состояние профиля'),
        ),
        migrations.AlterField(
            model_name='misconduct',
            name='status',
            field=models.CharField(choices=[('AD', 'Ожидает объяснение'), ('WT', 'Ожидает решение'), ('CL', 'Решение принято')], default='AD', max_length=10, verbose_name='Статус рассмотрения'),
        ),
        migrations.RunPython(setting_statuses),
        migrations.RemoveField(
            model_name='profile',
            name='confirmation_link_sent',
        ),
        migrations.RemoveField(
            model_name='profile',
            name='email_is_confirmed',
        ),
    ]
