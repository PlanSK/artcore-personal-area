# Generated by Django 4.0.4 on 2022-08-06 16:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('salary', '0013_chat_message'),
    ]



    operations = [
        migrations.AlterModelOptions(
            name='chat',
            options={'permissions': [('can_create_new_chats', 'Can create new chats')], 'verbose_name': 'Chat'},
        ),
    ]
