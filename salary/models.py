from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse_lazy

from salary.services.profile_services import get_expirience_string
from salary.services.filesystem import (
    user_directory_path,
    OverwriteStorage,
)
from salary.services.earnings import (
    WorkshiftData, get_current_earnings, get_total_revenue,
    get_game_zone_subtotal, get_workshift_penalties, get_costs_sum,
    get_errors_sum
)


def get_last_name(self):
    return f'{self.last_name} {self.first_name}'

User.add_to_class("get_full_name", get_last_name)


class Profile(models.Model):
    class EmailStatus(models.TextChoices):
        ADDED = 'ADD', 'Не подтвержден'
        SENT = 'SNT', 'Ссылка направлена'
        CONFIRMED = 'CNF', 'Подтвержден'

    class ProfileStatus(models.TextChoices):
        REGISTRED = 'RG', 'Ожидает разрешение'
        AUTHENTICATED = 'AU', 'Письмо направлено'
        WAIT = 'WT', 'Ожидает проверки'
        VERIFIED = 'VD', 'Проверен'
        DISMISSED = 'DSM', 'Уволен'

    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                primary_key=True)
    birth_date = models.DateField(null=True, verbose_name='Дата рождения')
    employment_date = models.DateField(null=True, 
                                       verbose_name='Дата трудоустройства')
    position = models.ForeignKey(
        'Position', on_delete=models.PROTECT, 
        null=True, verbose_name='Должность'
    )
    attestation_date = models.DateField(
        blank=True, null=True, 
        verbose_name='Дата прохождения аттестации'
    )
    dismiss_date = models.DateField(
        blank=True, null=True, verbose_name='Дата увольнения'
    )
    photo = models.ImageField(
        blank=True, null=True, storage=OverwriteStorage(), 
        upload_to=user_directory_path, verbose_name='Фото профиля')
    email_status = models.CharField(
        max_length=10, choices=EmailStatus.choices,
        default=EmailStatus.ADDED, verbose_name='Состояние электронной почты'
    )
    profile_status = models.CharField(
        max_length=10, 
        choices=ProfileStatus.choices,
        default=ProfileStatus.REGISTRED,
        verbose_name='Состояние профиля'
    )
    profile_comment = models.TextField(
        verbose_name='Комментарий',
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self) -> str:
        return f'{self.user.last_name} [{self.user.username}]'

    class Meta:
        verbose_name = 'Профиль сотрудника'
        verbose_name_plural = 'Профили сотрудников'

    def get_experience_text(self) -> str:
        return get_expirience_string(employment_date=self.employment_date,
                                     expiration_date=self.dismiss_date)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        instance.profile = Profile.objects.create(user=instance)
    instance.profile.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class DisciplinaryRegulations(models.Model):
    article = models.CharField(max_length=10, verbose_name='Пункт')
    title = models.CharField(max_length=255, verbose_name='Наименование')
    base_penalty = models.FloatField(default=0.0, verbose_name='Сумма штрафа')
    sanction = models.CharField(max_length=255, verbose_name='Санкция',
                                blank=True, null=True)

    class Meta:
        verbose_name = 'Пункт регламента'
        verbose_name_plural = 'Дисциплинарный регламент'

    def __str__(self) -> str:
        return f'{self.article} {self.title}'


class Misconduct(models.Model):
    class MisconductStatus(models.TextChoices):
        ADDED = 'AD', 'Ожидает объяснение'
        WAIT = 'WT', 'На рассмотрении'
        CLOSED = 'CL', 'Решение принято'

    misconduct_date = models.DateField(verbose_name='Дата нарушения')
    workshift_date = models.DateField(verbose_name='Дата смены')
    intruder = models.ForeignKey(
        User, on_delete=models.PROTECT, 
        verbose_name='Сотрудник', related_name='intruder'
    )
    regulations_article = models.ForeignKey(
        DisciplinaryRegulations, on_delete=models.PROTECT,
        verbose_name='Пункт дисциплинарного регламента',
        default=settings.DEFAULT_MISCONDUCT_ARTICLE_NUMBER
    )
    penalty = models.FloatField(verbose_name='Сумма штрафа', default=0.0)
    explanation_exist = models.BooleanField(
        verbose_name='Наличие объяснительной', default=False
    )
    moderator = models.ForeignKey(
        User, on_delete=models.PROTECT, verbose_name='Арбитр (кто выявил)',
        related_name='moderator'
    )
    comment = models.TextField(verbose_name='Примечание', blank=True)
    status = models.CharField(
        max_length=10, choices=MisconductStatus.choices,
        default=MisconductStatus.ADDED, verbose_name='Статус рассмотрения'
    )
    slug = models.SlugField(
        max_length=60, unique=True, verbose_name='URL', null=True, blank=True
    )
    change_date = models.DateTimeField(
        verbose_name='Дата изменения', auto_now=True, null=True
    )
    editor = models.TextField(
        verbose_name='Редактор', blank=True, editable=False
    )

    class Meta:
        verbose_name = 'Дисциплинарный проступок'
        verbose_name_plural = 'Дисциплинарные проступки'
        ordering = ['-misconduct_date']

    def __str__(self) -> str:
        return f'{self.misconduct_date} {self.intruder.get_full_name()}'

    def get_absolute_url(self):
        return reverse_lazy('misconduct_detail', kwargs={'slug': self.slug})


class WorkingShift(models.Model):
    class WorkshiftStatus(models.TextChoices):
        NOT_CONFIRMED = 'NOT_CONFIRMED', 'Не подтверждена'
        UNVERIFIED = 'UVD', 'Не проверена'
        WAIT_CORRECTION = 'WTC', 'Ожидает исправления'
        VERIFIED = 'VFD', 'Проверена'
    
    hall_admin = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='hall_admin'
    )
    cash_admin = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='cash_admin'
    )
    shift_date = models.DateField(
        verbose_name='Дата смены', unique=True, db_index=True
    )
    next_hall_admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='next_hall_admin',
        blank=True, null=True
    )
    next_cashier = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='next_cashier',
        blank=True, null=True
    )
    hall_admin_arrival_time = models.TimeField(
        verbose_name='Время прибытия админа', blank=True, null=True
    )
    cashier_arrival_time = models.TimeField(
        verbose_name='Время прибытия кассира', blank=True, null=True
    )
    acquiring_evator_sum = models.FloatField(
        verbose_name='Сумма эквайринга (Эвотор)', default=0.0
    )
    acquiring_terminal_sum = models.FloatField(
        verbose_name='Сумма эквайринга (Терминал)', default=0.0
    )
    cost_sum = models.FloatField(verbose_name='Сумма расходов', default=0.0)
    cash_sum = models.FloatField(verbose_name='Сумма наличных', default=0.0)
    short_change_sum = models.FloatField(
        verbose_name='Сумма на сдачу', default=2000.0
    )
    bar_revenue = models.FloatField(
        verbose_name='Выручка по бару', default=0.0
    )
    game_zone_revenue = models.FloatField(
        verbose_name='Выручка игровой зоны (без доп. услуг)', default=0.0
    )
    game_zone_error = models.FloatField(
        verbose_name='Сумма ошибок', default=0.0
    )
    game_zone_subtotal = models.FloatField(
        verbose_name='Подытог по игоровой зоне', default=0.0
    )
    additional_services_revenue = models.FloatField(
        verbose_name='Выручка доп. услуги', default=0.0
    )
    hookah_revenue = models.FloatField(
        verbose_name='Выручка по кальянам', default=0.0
    )
    hall_cleaning = models.BooleanField(
        verbose_name='Наведение порядка', default=True
    )
    shortage = models.FloatField(verbose_name='Недостача', default=0.0)
    shortage_paid = models.BooleanField(
        verbose_name='Отметка о погашении недостачи', default=False
    )
    summary_revenue = models.FloatField(
        verbose_name='Суммарная выручка', default=0.0
    )
    slug = models.SlugField(
        max_length=60, unique=True, verbose_name='URL', null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=WorkshiftStatus.choices,
        default=WorkshiftStatus.NOT_CONFIRMED,
        verbose_name='Статус смены',
        db_column='shift_status'
    )
    comment_for_cash_admin = models.TextField(
        verbose_name='Примечание для кассира', blank=True
    )
    comment_for_hall_admin = models.TextField(
        verbose_name='Примечание для админа', blank=True
    )
    publication_link = models.TextField(
        verbose_name='СММ-публикация (ссылка)', blank=True
    )
    publication_is_verified = models.BooleanField(
        verbose_name='СММ-публикация проверена', default=False
    )
    change_date = models.DateTimeField(
        verbose_name='Дата изменения', auto_now=True, null=True
    )
    editor = models.TextField(
        verbose_name='Редактор', blank=True, editable=False
    )
    hall_admin_penalty = models.FloatField(
        verbose_name='Штраф администратора зала', default=0.0
    )
    cash_admin_penalty = models.FloatField(
        verbose_name='Штраф администратора кассы', default=0.0
    )
    technical_report = models.BooleanField(
        verbose_name='Технический отчёт', default=False
    )
    wishes = models.TextField(verbose_name='Предложения', blank=True)

    class Meta:
        verbose_name = 'Смена'
        verbose_name_plural = 'Смены'
        ordering = ['-shift_date']
        permissions = [
            ("view_workshift_report", "Can view monthly reports"),
            ("advanced_change_workshift",
             "Can edit the entire contents of the workingshift"),
        ]

    def __str__(self) -> str:
        return self.shift_date.strftime('%d-%m-%Y')


    def get_workshift_data(self):
        return WorkshiftData(
            shift_date=self.shift_date,
            bar_revenue=self.bar_revenue,
            game_zone_revenue=self.game_zone_subtotal,
            additional_services_revenue=self.additional_services_revenue,
            hookah_revenue=self.hookah_revenue,
            hall_cleaning=self.hall_cleaning,
            shortage=self.shortage,
            shortage_paid=self.shortage_paid,
            publication=self.publication_is_verified,
            admin_penalty=self.hall_admin_penalty,
            cashier_penalty=self.cash_admin_penalty
        )


    @property
    def hall_admin_earnings(self):
        workshift_data = self.get_workshift_data()
        employee = self.hall_admin
        return get_current_earnings(employee, workshift_data)


    @property
    def cashier_earnings(self):
        workshift_data = self.get_workshift_data()
        employee = self.cash_admin
        return get_current_earnings(employee, workshift_data, is_cashier=True)

    def get_absolute_url(self):
        return reverse_lazy('detail_workshift', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        self.slug = self.shift_date
        self.game_zone_error = get_errors_sum(
            ErrorKNA.objects.filter(workshift__id=self.pk))
        self.cost_sum = get_costs_sum(
            Cost.objects.filter(workshift__id=self.pk))
        self.game_zone_subtotal = get_game_zone_subtotal(
            self.game_zone_revenue, self.game_zone_error)
        self.summary_revenue = get_total_revenue(
            self.bar_revenue, self.game_zone_subtotal,
            self.additional_services_revenue, self.hookah_revenue
        )

        current_penalties = get_workshift_penalties(
            misconduct_queryset=Misconduct.objects.filter(
                workshift_date=self.shift_date,
                status=Misconduct.MisconductStatus.CLOSED,
            ),
            cash_admin_id=self.cash_admin.pk,
            hall_admin_id=self.hall_admin.pk
        )
        self.cash_admin_penalty = current_penalties.cash_admin_penalty
        self.hall_admin_penalty = current_penalties.hall_admin_penalty

        super().save(*args, **kwargs)


@receiver(post_save, sender=Misconduct)
@receiver(post_delete, sender=Misconduct)
def run_calculating_penalties(sender, instance, created=None, **kwargs):
    workshift_queryset = WorkingShift.objects.filter(
            shift_date=instance.workshift_date
    ).first()
    if workshift_queryset:
        workshift_queryset.save()


class Position(models.Model):
    title = models.CharField(max_length=255)
    name = models.CharField(max_length=60)
    position_salary = models.FloatField(default=0.0)

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'

    def __str__(self) -> str:
        return self.title


class Chat(models.Model):
    members = models.ManyToManyField(User, verbose_name='Участники')
    slug = models.SlugField(
        max_length=60, unique=True, verbose_name='URL', null=True, blank=True
    )

    class Meta:
        verbose_name = 'Chat'
        permissions = [
            ("can_create_new_chats", "Can create new chats"),
        ]

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        if not self.slug:
            self.slug = f'chat_id{self.id}'
            self.save()
    
    def get_absolute_url(self):
        return reverse_lazy('messenger_open_chat', kwargs={'slug': self.slug})


class Message(models.Model):
    chat = models.ForeignKey(
        Chat, on_delete=models.CASCADE, related_name='chat', verbose_name='Чат'
    )
    message_text = models.TextField(verbose_name='Текст сообщения')
    author = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='author', verbose_name='Автор'
    )
    sending_time = models.DateTimeField(
        verbose_name='Время отправления', auto_now_add=True
    )
    is_read = models.BooleanField(
        verbose_name='Отметка о прочтении', default=False
    )

    class Meta:
        verbose_name = 'Message'


class ErrorKNA(models.Model):
    class ErrorType(models.TextChoices):
        KNA = 'KNA', 'Ошибка по КНА'
        GRILL = 'GRILL', 'Гриль'
        LOTTO = 'LOTTO', 'Лото'
    error_type = models.CharField(
        max_length=20, choices=ErrorType.choices, default=ErrorType.KNA,
        verbose_name='Тип ошибки')
    error_time = models.TimeField(verbose_name='Время ошибки')
    card = models.CharField(max_length=128,
                            verbose_name='Номер компьютера или карты')
    error_sum = models.FloatField(verbose_name='Сумма ошибки', default=0.0)
    description = models.CharField(max_length=255, verbose_name='Описание',
                                   blank=True, null=True)
    workshift = models.ForeignKey(WorkingShift, on_delete=models.CASCADE,
                                  related_name='errors')


class Cost(models.Model):
    cost_sum = models.FloatField(verbose_name='Сумма расхода', default=0.0)
    cost_reason = models.CharField(max_length=255, verbose_name='Причина')
    cost_person = models.ForeignKey(User, on_delete=models.PROTECT,
                                    verbose_name='Кто потратил')
    workshift = models.ForeignKey(WorkingShift, on_delete=models.CASCADE,
                                  related_name='costs')


class CabinError(models.Model):
    time = models.TimeField(verbose_name='Время ошибки')
    cabin_number = models.IntegerField(choices=((i, str(i))
                                                for i in range(1,7)),
                                       verbose_name='Номер кабинки')
    description = models.CharField(max_length=255, verbose_name='Причина')
    error_interval = models.CharField(max_length=255,
                                      verbose_name='Ошибочное время')
    workshift = models.ForeignKey(WorkingShift, on_delete=models.CASCADE,
                                  related_name='cabin_error')
