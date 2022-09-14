# Generated by Django 4.1 on 2022-09-14 19:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import salary.models
import salary.utils


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Chat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(blank=True, max_length=60, null=True, unique=True, verbose_name='URL')),
                ('members', models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Участники')),
            ],
            options={
                'verbose_name': 'Chat',
                'permissions': [('can_create_new_chats', 'Can create new chats')],
            },
        ),
        migrations.CreateModel(
            name='DisciplinaryRegulations',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('article', models.CharField(max_length=10, verbose_name='Пункт')),
                ('title', models.CharField(max_length=255, verbose_name='Наименование')),
                ('base_penalty', models.FloatField(default=0.0, verbose_name='Сумма штрафа')),
                ('sanction', models.CharField(blank=True, max_length=255, null=True, verbose_name='Санкция')),
            ],
            options={
                'verbose_name': 'Пункт регламента',
                'verbose_name_plural': 'Дисциплинарный регламент',
            },
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=60)),
                ('position_salary', models.FloatField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Должность',
                'verbose_name_plural': 'Должности',
            },
        ),
        migrations.CreateModel(
            name='WorkingShift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('shift_date', models.DateField(db_index=True, unique=True, verbose_name='Дата смены')),
                ('bar_revenue', models.FloatField(default=0.0, verbose_name='Выручка по бару')),
                ('game_zone_revenue', models.FloatField(default=0.0, verbose_name='Выручка игровой зоны (без доп. услуг)')),
                ('game_zone_error', models.FloatField(default=0.0, verbose_name='Сумма ошибок')),
                ('game_zone_subtotal', models.FloatField(default=0.0, verbose_name='Подытог по игоровой зоне')),
                ('vr_revenue', models.FloatField(default=0.0, verbose_name='Выручка доп. услуги и VR')),
                ('hookah_revenue', models.FloatField(default=0.0, verbose_name='Выручка по кальянам')),
                ('hall_cleaning', models.BooleanField(default=True, verbose_name='Наведение порядка')),
                ('shortage', models.FloatField(default=0.0, verbose_name='Недостача')),
                ('shortage_paid', models.BooleanField(default=False, verbose_name='Отметка о погашении недостачи')),
                ('summary_revenue', models.FloatField(default=0.0, verbose_name='Суммарная выручка')),
                ('slug', models.SlugField(blank=True, max_length=60, null=True, unique=True, verbose_name='URL')),
                ('is_verified', models.BooleanField(db_index=True, default=False, verbose_name='Проверено')),
                ('comment_for_cash_admin', models.TextField(blank=True, verbose_name='Примечание для кассира')),
                ('comment_for_hall_admin', models.TextField(blank=True, verbose_name='Примечание для админа')),
                ('publication_link', models.TextField(blank=True, verbose_name='СММ-публикация (ссылка)')),
                ('publication_is_verified', models.BooleanField(default=False, verbose_name='СММ-публикация проверена')),
                ('change_date', models.DateTimeField(auto_now=True, null=True, verbose_name='Дата изменения')),
                ('editor', models.TextField(blank=True, editable=False, verbose_name='Редактор')),
                ('hall_admin_penalty', models.FloatField(default=0.0, verbose_name='Штраф администратора зала')),
                ('cash_admin_penalty', models.FloatField(default=0.0, verbose_name='Штраф администратора кассы')),
                ('cash_admin', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cash_admin', to=settings.AUTH_USER_MODEL)),
                ('hall_admin', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='hall_admin', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Смена',
                'verbose_name_plural': 'Смены',
                'ordering': ['-shift_date'],
                'permissions': [('view_workshift_report', 'Can view monthly reports'), ('advanced_change_workshift', 'Can edit the entire contents of the workingshift')],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('birth_date', models.DateField(null=True, verbose_name='Дата рождения')),
                ('employment_date', models.DateField(null=True, verbose_name='Дата трудоустройства')),
                ('attestation_date', models.DateField(blank=True, null=True, verbose_name='Дата прохождения аттестации')),
                ('dismiss_date', models.DateField(blank=True, null=True, verbose_name='Дата увольнения')),
                ('photo', models.ImageField(blank=True, null=True, storage=salary.utils.OverwriteStorage(), upload_to=salary.models.user_directory_path, verbose_name='Фото профиля')),
                ('email_status', models.CharField(choices=[('ADD', 'Не подтвержден'), ('SNT', 'Ссылка направлена'), ('CNF', 'Подтвержден')], default='ADD', max_length=10, verbose_name='Состояние электронной почты')),
                ('profile_status', models.CharField(choices=[('RG', 'Ожидает разрешение'), ('AU', 'Письмо направлено'), ('WT', 'Ожидает проверки'), ('VD', 'Проверен'), ('DSM', 'Уволен')], default='RG', max_length=10, verbose_name='Состояние профиля')),
                ('position', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='salary.position', verbose_name='Должность')),
            ],
            options={
                'verbose_name': 'Профиль сотрудника',
                'verbose_name_plural': 'Профили сотрудников',
            },
        ),
        migrations.CreateModel(
            name='Misconduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('misconduct_date', models.DateField(verbose_name='Дата нарушения')),
                ('workshift_date', models.DateField(verbose_name='Дата смены')),
                ('penalty', models.FloatField(default=0.0, verbose_name='Сумма штрафа')),
                ('explanation_exist', models.BooleanField(default=False, verbose_name='Наличие объяснительной')),
                ('comment', models.TextField(blank=True, verbose_name='Примечание')),
                ('status', models.CharField(choices=[('AD', 'Ожидает объяснение'), ('WT', 'На рассмотрении'), ('CL', 'Решение принято')], default='AD', max_length=10, verbose_name='Статус рассмотрения')),
                ('slug', models.SlugField(blank=True, max_length=60, null=True, unique=True, verbose_name='URL')),
                ('change_date', models.DateTimeField(auto_now=True, null=True, verbose_name='Дата изменения')),
                ('editor', models.TextField(blank=True, editable=False, verbose_name='Редактор')),
                ('intruder', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='intruder', to=settings.AUTH_USER_MODEL, verbose_name='Сотрудник')),
                ('moderator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='moderator', to=settings.AUTH_USER_MODEL, verbose_name='Арбитр (кто выявил)')),
                ('regulations_article', models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='salary.disciplinaryregulations', verbose_name='Пункт дисциплинарного регламента')),
            ],
            options={
                'verbose_name': 'Дисциплинарный проступок',
                'verbose_name_plural': 'Дисциплинарные проступки',
                'ordering': ['-misconduct_date'],
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_text', models.TextField(verbose_name='Текст сообщения')),
                ('sending_time', models.DateTimeField(auto_now_add=True, verbose_name='Время отправления')),
                ('is_read', models.BooleanField(default=False, verbose_name='Отметка о прочтении')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author', to=settings.AUTH_USER_MODEL, verbose_name='Автор')),
                ('chat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat', to='salary.chat', verbose_name='Чат')),
            ],
            options={
                'verbose_name': 'Message',
            },
        ),
    ]
