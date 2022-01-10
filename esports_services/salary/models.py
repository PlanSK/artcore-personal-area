from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

import datetime


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    birth_date = models.DateField(null=True, verbose_name='Дата рождения')
    employment_date = models.DateField(default=timezone.now, verbose_name='Дата трудоустройства')
    position = models.ForeignKey('Position', on_delete=models.PROTECT, null=True)
    attestation_date = models.DateField(blank=True, null=True, verbose_name='Дата прохождения аттестации')

    def __str__(self) -> str:
        return f'{self.user.first_name} {self.user.last_name} [{self.user.username}]'
    
    def get_name(self) -> str:
        return f'{self.user.first_name} {self.user.last_name}'

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            instance.profile = Profile.objects.create(user=instance)
        instance.profile.save()

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()

    class Meta:
        verbose_name = 'Профиль сотрудника'
        verbose_name_plural = 'Профили сотрудников'


class WorkingShift(models.Model):
    hall_admin = models.ForeignKey(User, on_delete=models.PROTECT, related_name='hall_admin')
    cash_admin = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cash_admin')
    shift_date = models.DateField(verbose_name='Дата смены', unique=True)
    bar_revenue = models.FloatField(verbose_name='Выручка по бару', default=0.0)
    game_zone_revenue = models.FloatField(verbose_name='Выручка игровой зоны', default=0.0)
    game_zone_error = models.FloatField(verbose_name='Сумма ошибок', default=0.0)
    vr_revenue = models.FloatField(verbose_name='Выручка доп. услуги и VR', default=0.0)
    hall_cleaning = models.BooleanField(default=False, verbose_name='Наведение порядка')
    hall_admin_discipline = models.BooleanField(default=True, verbose_name='Сюблюдение дисциплины Админ зала')
    cash_admin_discipline = models.BooleanField(default=True, verbose_name='Сюблюдение дисциплины Админ кассы')
    shortage = models.FloatField(default=0, verbose_name='Недостача')
    shortage_paid = models.BooleanField(default=False, verbose_name="Отметка о погашении недостачи")
    slug = models.SlugField(max_length=60, unique=True, verbose_name='URL', null=True, blank=True)
    is_verified = models.BooleanField(default=False, verbose_name='Проверено')
    comment = models.TextField(verbose_name='Примечание', blank=True)

    class Meta:
        verbose_name = 'Смена'
        verbose_name_plural = 'Смены'

    def __str__(self) -> str:
        return self.shift_date.strftime('%d-%m-%Y')

    def save(self):
        super(WorkingShift, self).save()
        self.slug = self.shift_date
        super(WorkingShift, self).save()
    
    def get_summary_revenue(self):
        summary_revenue = sum([
            self.bar_revenue,
            self.game_zone_revenue,
            self.vr_revenue,
            -self.game_zone_error
        ])
        return summary_revenue
    
    def kpi_salary_calculate(self, current_user) -> float:
        kpi_data = {
            'experience': 0.0,
            'discipline': 0.0,
            'attestation': 0.0,
        }
        kpi_criteria = {
            'hall_admin': {
                'bar' : [(0, 0.005), (3000, 0.01), (4000, 0.02), (6000, 0.025), (8000, 0.03)],
                'game_zone':[(0, 0.005), (20000, 0.01), (25000, 0.0125), (27500, 0.015), (30000, 0.0175)],
                'vr': [(0, 0.1), (1000, 0.12), (2000, 0.13), (3000, 0.14), (5000, 0.15)]
            },
            'cash_admin': {
                'bar' : [(0, 0.03), (3000, 0.04), (4000, 0.05), (6000, 0.06), (8000, 0.07)],
                'game_zone':[(0, 0.005), (20000, 0.01), (25000, 0.0125), (27500, 0.015), (30000, 0.0175)],
                'vr': [(0, 0.05), (1000, 0.06), (2000, 0.065), (3000, 0.07), (5000, 0.075)]
            }
        }
        experience_bonus = 200
        hall_cleaning_bonus = 400
        attestation_bonus = 200
        discipline_bonus = 1000

        # Position salary
        shift_salary = current_user.profile.position.position_salary

        if current_user.profile.position.name == 'hall_admin':
            kpi_ratio = kpi_criteria['hall_admin']
            discipline = self.hall_admin_discipline
            hall_cleaning = self.hall_cleaning
        elif current_user.profile.position.name == 'cash_admin':
            kpi_ratio = kpi_criteria['cash_admin']
            hall_cleaning = False
            discipline = self.cash_admin_discipline
            if self.shortage and not self.shortage_paid:
                shift_salary = round(shift_salary - self.shortage * 2, 2)
        else:
            raise ValueError('Position settings is not defined.')

        # Expirience calc
        experience = (self.shift_date - current_user.profile.employment_date).days
        
        if experience > 90:
            kpi_data['experience'] = experience_bonus
            shift_salary += experience_bonus

        # Discipline
        if discipline:
            kpi_data['discipline'] = discipline_bonus
            shift_salary += discipline_bonus

        # Hall cleaning
        if hall_cleaning:
            shift_salary += hall_cleaning_bonus

        # Attestation
        if current_user.profile.attestation_date and current_user.profile.attestation_date <= self.shift_date:
            kpi_data['attestation'] = attestation_bonus
            shift_salary += attestation_bonus

        # KPI
        for revenue_value, ratio in kpi_ratio['bar']:
            if self.bar_revenue >= revenue_value:
                kpi_data['bar'] = (self.bar_revenue * ratio, ratio * 100)

        game_zone_revenue = self.game_zone_revenue - self.game_zone_error
        for revenue_value, ratio in kpi_ratio['game_zone']:
            if game_zone_revenue >= revenue_value:
                kpi_data['game_zone'] = (game_zone_revenue * ratio, ratio * 100)

        for revenue_value, ratio in kpi_ratio['vr']:
            if self.vr_revenue >= revenue_value:
                kpi_data['vr'] = (self.vr_revenue * ratio, ratio * 100)

        shift_salary += sum([kpi_data['bar'][0], kpi_data['game_zone'][0], kpi_data['vr'][0]])

        kpi_data['shift_salary'] = shift_salary

        return kpi_data


class Position(models.Model):
    title = models.CharField(max_length=255)
    name = models.CharField(max_length=60)
    position_salary = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'

    def __str__(self) -> str:
        return self.title