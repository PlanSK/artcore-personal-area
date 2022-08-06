# Generated by Django 4.0.4 on 2022-08-06 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('salary', '0014_alter_chat_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='profile_status',
            field=models.CharField(choices=[('RG', 'Ожидает разрешение'), ('AU', 'Письмо направлено'), ('WT', 'Ожидает проверки'), ('VD', 'Проверен'), ('DSM', 'Уволен')], default='RG', max_length=10, verbose_name='Состояние профиля'),
        ),
    ]
