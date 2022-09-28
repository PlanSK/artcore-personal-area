import datetime
from dateutil.relativedelta import relativedelta

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse_lazy

from .config import *
from salary.services.profile_services import (
    get_expirience_string
)
from salary.services.filesystem import (
    user_directory_path,
    OverwriteStorage,
)
from salary.services.workshift import WorkshiftData


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
        default=DEFAULT_MISCONDUCT_ARTICLE_NUMBER
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

    def save(self, *args, **kwargs):
        if (self.explanation_exist and
                self.status == self.MisconductStatus.ADDED):
            self.status = self.MisconductStatus.WAIT
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse_lazy('misconduct_detail', kwargs={'slug': self.slug})


class WorkingShift(models.Model):
    hall_admin = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='hall_admin'
    )
    cash_admin = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='cash_admin'
    )
    shift_date = models.DateField(
        verbose_name='Дата смены', unique=True, db_index=True
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
    vr_revenue = models.FloatField(
        verbose_name='Выручка доп. услуги и VR', default=0.0
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
    is_verified = models.BooleanField(
        verbose_name='Проверено', default=False, db_index=True
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
            vr_revenue=self.vr_revenue,
            hookah_revenue=self.hookah_revenue,
            shortage=self.shortage,
            shortage_paid=self.shortage_paid,
            publication=self.publication_is_verified,
            admin_penalty=self.hall_admin_penalty,
            cashier_penalty=self.cash_admin_penalty
        )


    def get_hall_admin_earnings(self):
        workshift_data = self.get_workshift_data()
        employee = self.hall_admin

     # Earnings block (must moved to services)


    def get_experience_bonus(self, employee) -> float:
        current_experience = (self.shift_date - employee.profile.employment_date).days
        if REQUIRED_EXPERIENCE <= current_experience:
            return EXPERIENCE_BONUS

        return 0.0

    def get_publication_bonus(self) -> float:
        if self.publication_link and self.publication_is_verified:
            return PUBLICATION_BONUS

        return 0.0

    def get_attestation_bonus(self, employee) -> float:
        if (employee.profile.attestation_date and
                employee.profile.attestation_date <= self.shift_date):
            return ATTESTATION_BONUS

        return 0.0

    def get_revenue_bonuses(self, criteria: dict) -> dict:
        revenue_tuple = (
            self.bar_revenue,
            self.game_zone_subtotal,
            self.vr_revenue
        )

        result_list = []
        for revenue, current_critera in zip(revenue_tuple, criteria.values()):
            criteria_ratio = list(
                filter(lambda x: x[0] <= revenue, current_critera))[-1][1]
            result_list.append((round(revenue * criteria_ratio, 2),
                                round(criteria_ratio * 100, 1)))

        return {
            'bar': result_list[0],
            'game_zone': result_list[1],
            'vr': result_list[2]
        }

    def employee_earnings_calc(self, employee) -> dict:
        base_earnings = {
            'salary': 0.0,
            'experience': 0.0,
            'penalty': 0.0,
            'award': 0.0,
            'attestation': 0.0,
            'publication_bonus': 0.0,
            'game_zone': (0.0, 0.0),
            'bar': (0.0, 0.0),
            'vr': (0.0, 0.0),
            'basic_part': 0.0,
            'bonus_part': 0.0,
            'retention': 0.0,
            'estimated_earnings': 0.0,
            'final_earnings': 0.0,
            'cleaning': 0.0,
            'hookah': 0.0,
            'before_shortage': 0.0,
        }
        if employee.profile.position.name != 'trainee':
            base_earnings.update({
                'salary': employee.profile.position.position_salary,
                'experience': self.get_experience_bonus(employee),
                'penalty': 0.0,
                'award': DISCIPLINE_AWARD,
                'attestation': self.get_attestation_bonus(employee),
                'publication_bonus': self.get_publication_bonus(),
                'game_zone': (0.0, 0.0),
                'bar': (0.0, 0.0),
                'vr': (0.0, 0.0),
            })

        return base_earnings

    def final_earnings_calculation(self, earnings: dict) -> dict:
        tuple_fields = ('bar', 'game_zone', 'vr')
        exclude_bonus_fields = ('salary', 'penalty',
                                'experience', 'attestation')
        bonus_part = 0.0

        for key, value in earnings.items():
            if key not in exclude_bonus_fields:
                if key not in tuple_fields:
                    bonus_part += value
                else:
                    bonus_part += value[0]

        if bonus_part > earnings['penalty']:
            remaining_bonus_part = bonus_part - earnings['penalty']
        else: 
            remaining_bonus_part = 0.0

        basic_part = sum([
                earnings.get('salary'),
                earnings.get('experience'),
                earnings.get('attestation')
        ])

        return {
            'basic_part': round(basic_part, 2),
            'bonus_part': round(bonus_part, 2),
            'retention': round(bonus_part - remaining_bonus_part, 2),
            'estimated_earnings': round(bonus_part + basic_part, 2),
            'final_earnings': round(remaining_bonus_part + basic_part,2),
        }

    def hall_admin_earnings_calc(self) -> dict:
        earnings = self.employee_earnings_calc(self.hall_admin)
        if self.hall_admin.profile.position.name != 'trainee':
            earnings['penalty'] = self.hall_admin_penalty
            if self.hall_cleaning:
                earnings['cleaning'] = HALL_CLEANING_BONUS
            earnings['hookah'] = round(
                self.hookah_revenue * HOOKAH_BONUS_RATIO, 2
            )
            earnings.update(self.get_revenue_bonuses(ADMIN_BONUS_CRITERIA))
            earnings.update(self.final_earnings_calculation(earnings))

        return earnings

    def cashier_earnings_calc(self) -> dict:
        earnings = self.employee_earnings_calc(self.cash_admin)
        if self.cash_admin.profile.position.name != 'trainee':
            earnings['penalty'] = self.cash_admin_penalty
            earnings.update(self.get_revenue_bonuses(CASHIER_BONUS_CRITERIA))
            earnings.update(self.final_earnings_calculation(earnings))
            earnings['before_shortage'] = earnings['final_earnings']
            if self.shortage and not self.shortage_paid:
                earnings['final_earnings'] = (
                    round(earnings['final_earnings'] - self.shortage * 2, 2)
                )
        return earnings

    def get_absolute_url(self):
        return reverse_lazy('detail_workshift', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        self.game_zone_subtotal = 0.0
        self.summary_revenue = 0.0
        
        if self.game_zone_revenue >= self.game_zone_error:
            self.game_zone_subtotal = round(
                self.game_zone_revenue - self.game_zone_error, 2
            ) 

        total_revenue = sum((
            self.bar_revenue,
            self.game_zone_subtotal,
            self.vr_revenue,
            self.hookah_revenue,
        ))
        if total_revenue > 0.0:
            self.summary_revenue = round(total_revenue, 2)

        misconduct_queryset = Misconduct.objects.filter(
            workshift_date=self.shift_date,
            status=Misconduct.MisconductStatus.CLOSED,
        )
        self.cash_admin_penalty = 0.0
        self.hall_admin_penalty = 0.0
        for misconduct in misconduct_queryset:
            if misconduct.intruder == self.cash_admin:
                self.cash_admin_penalty += misconduct.penalty
            elif misconduct.intruder == self.hall_admin:
                self.hall_admin_penalty += misconduct.penalty

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
