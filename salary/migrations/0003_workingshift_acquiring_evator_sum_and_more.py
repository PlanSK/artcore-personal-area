# Generated by Django 4.1 on 2023-04-09 09:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('salary', '0002_profile_profile_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='workingshift',
            name='acquiring_evator_sum',
            field=models.FloatField(default=0.0, verbose_name='Сумма эквайринга (Эватор)'),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='acquiring_terminal_sum',
            field=models.FloatField(default=0.0, verbose_name='Сумма эквайринга (Терминал)'),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='cash_sum',
            field=models.FloatField(default=0.0, verbose_name='Сумма наличных'),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='cashier_arrival_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Время прибытия кассира'),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='cost_sum',
            field=models.FloatField(default=0.0, verbose_name='Сумма расходов'),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='hall_admin_arrival_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Время прибытия админа'),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='next_cashier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_cashier', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='next_hall_admin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_hall_admin', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='short_change_sum',
            field=models.FloatField(default=2000.0, verbose_name='Сумма на сдачу'),
        ),
        migrations.AddField(
            model_name='workingshift',
            name='technical_report',
            field=models.BooleanField(default=False, verbose_name='Технический отчёт'),
        ),
        migrations.AlterField(
            model_name='workingshift',
            name='status',
            field=models.CharField(choices=[('NOT_CONFIRMED', 'Не подтверждена'), ('UVD', 'Не проверена'), ('WTC', 'Ожидает исправления'), ('VFD', 'Проверена')], db_column='shift_status', default='NOT_CONFIRMED', max_length=20, verbose_name='Статус смены'),
        ),
        migrations.CreateModel(
            name='ErrorKNA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('error_type', models.CharField(choices=[('KNA', 'Ошибка по КНА'), ('GRILL', 'Гриль'), ('LOTTO', 'Лото')], default='KNA', max_length=20, verbose_name='Тип ошибки')),
                ('error_time', models.TimeField(verbose_name='Время ошибки')),
                ('card', models.CharField(max_length=128, verbose_name='Номер компьютера или карты')),
                ('error_sum', models.FloatField(default=0.0, verbose_name='Сумма ошибки')),
                ('description', models.CharField(blank=True, max_length=255, null=True, verbose_name='Описание')),
                ('workshift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='errors', to='salary.workingshift')),
            ],
        ),
        migrations.CreateModel(
            name='Cost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cost_sum', models.FloatField(default=0.0, verbose_name='Сумма расхода')),
                ('cost_reason', models.CharField(max_length=255, verbose_name='Причина')),
                ('cost_person', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Кто потратил')),
                ('workshift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='costs', to='salary.workingshift')),
            ],
        ),
    ]