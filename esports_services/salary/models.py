from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

import datetime
from dateutil.relativedelta import relativedelta


HOURS_VARIANT = ('час', 'часа', 'часов')
DAYS_VARIANT = ('день', 'дня', 'дней')
MONTH_VARIANT = ('месяц','месяца','месяцев')
YEARS_VARIANT = ('год', 'года', 'лет')


def user_directory_path(instance, filename):
    return 'user_{0}/{1}'.format(instance.user.id, filename)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    birth_date = models.DateField(null=True, verbose_name='Дата рождения')
    employment_date = models.DateField(null=True, verbose_name='Дата трудоустройства')
    position = models.ForeignKey('Position', on_delete=models.PROTECT, null=True, verbose_name='Должность')
    attestation_date = models.DateField(blank=True, null=True, verbose_name='Дата прохождения аттестации')
    dismiss_date = models.DateField(blank=True, null=True, verbose_name='Дата увольнения')
    photo = models.ImageField(blank=True, null=True, upload_to=user_directory_path, verbose_name='Фото профиля')

    def __str__(self) -> str:
        return f'{self.user.first_name} {self.user.last_name} [{self.user.username}]'

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

    def get_choice_plural(self, amount, variants):
        if amount % 10 == 1 and amount % 100 != 11:
            choice = 0
        elif amount % 10 >= 2 and amount % 10 <= 4 and \
                (amount % 100 < 10 or amount % 100 >= 20):
            choice = 1
        else:
            choice = 2

        return variants[choice]

    def get_work_experience(self):
        end_date = self.dismiss_date if self.dismiss_date else datetime.date.today()
        experience = relativedelta(end_date, self.employment_date)
        days, months, years = experience.days, experience.months, experience.years
        experience_text = ''

        if years:
            experience_text = f'{years} {self.get_choice_plural(years, YEARS_VARIANT)} '

        if months:
            experience_text += f'{months} {self.get_choice_plural(months, MONTH_VARIANT)} '

        if days or not experience_text:
            experience_text += f'{days} {self.get_choice_plural(days, DAYS_VARIANT)}'

        return experience_text

    def get_last_login(self) -> str:
        if self.user.last_login:
            date_period = relativedelta(datetime.date.today(), self.user.last_login.date())
            hours_period = relativedelta(timezone.now(), self.user.last_login)
            if date_period.days == 0 and 1 < hours_period.hours < 12:
                return f'{self.get_choice_plural(hours_period.hours, HOURS_VARIANT)} назад'
            elif date_period.days == 0 and hours_period.hours > 12:
                return f'сегодня в {self.user.last_login.strftime("%H:%M")}'
            elif date_period.days == 1:
                return f'вчера в {self.user.last_login.strftime("%H:%M")}'
            elif 1 < date_period.days < 7:
                return f'{date_period.days} {self.get_choice_plural(date_period.days, DAYS_VARIANT)} назад'
            elif date_period.days == 7:
                return 'неделю назад'
            else:
                return self.user.last_login
        return None


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
    hall_admin_discipline_penalty = models.FloatField(default=0.0, verbose_name='Дисциплинарный штраф')
    cash_admin_discipline = models.BooleanField(default=True, verbose_name='Сюблюдение дисциплины Админ кассы')
    cash_admin_discipline_penalty = models.FloatField(default=0.0, verbose_name='Дисциплинарный штраф')
    shortage = models.FloatField(default=0, verbose_name='Недостача')
    shortage_paid = models.BooleanField(default=False, verbose_name="Отметка о погашении недостачи")
    slug = models.SlugField(max_length=60, unique=True, verbose_name='URL', null=True, blank=True)
    is_verified = models.BooleanField(default=False, verbose_name='Проверено')
    comment = models.TextField(verbose_name='Примечание', blank=True)

    class Meta:
        verbose_name = 'Смена'
        verbose_name_plural = 'Смены'
        ordering = ['-shift_date']

    def __str__(self) -> str:
        return self.shift_date.strftime('%d-%m-%Y')

    def save(self, *args, **kwargs):
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
            'cleaning': 0.0
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
        experience_bonus = 200.0
        hall_cleaning_bonus = 400.0
        attestation_bonus = 200.0
        discipline_bonus = 1000.0
        penalty = 0.0

        # Position salary
        shift_salary = current_user.profile.position.position_salary
        calculated_salary = shift_salary + discipline_bonus
        if current_user.profile.position.name == 'hall_admin':
            calculated_salary += hall_cleaning_bonus
            kpi_ratio = kpi_criteria['hall_admin']
            discipline = self.hall_admin_discipline
            penalty = self.hall_admin_discipline_penalty
            hall_cleaning = self.hall_cleaning
        elif current_user.profile.position.name == 'cash_admin':
            kpi_ratio = kpi_criteria['cash_admin']
            hall_cleaning = False
            discipline = self.cash_admin_discipline
            penalty = self.cash_admin_discipline_penalty
            if self.shortage and not self.shortage_paid:
                shift_salary = round(shift_salary - self.shortage * 2, 2)
        else:
            raise ValueError('Position settings is not defined.')

        # Expirience calc
        experience = (self.shift_date - current_user.profile.employment_date).days

        if experience > 90:
            kpi_data['experience'] = experience_bonus
            calculated_salary += experience_bonus
            shift_salary += experience_bonus

        # Discipline
        if discipline_bonus <= penalty:
            discipline_bonus = 0
        else:
            discipline_bonus -= penalty

        kpi_data['discipline'] = discipline_bonus
        kpi_data['penalty'] = penalty
        shift_salary += discipline_bonus

        # Hall cleaning
        if hall_cleaning:
            kpi_data['cleaning'] = hall_cleaning_bonus
            shift_salary += hall_cleaning_bonus

        # Attestation
        if current_user.profile.attestation_date and current_user.profile.attestation_date <= self.shift_date:
            kpi_data['attestation'] = attestation_bonus
            calculated_salary += attestation_bonus
            shift_salary += attestation_bonus

        # KPI
        for revenue_value, ratio in kpi_ratio['bar']:
            if self.bar_revenue >= revenue_value:
                kpi_data['bar'] = (self.bar_revenue * ratio, ratio * 100)

        game_zone_revenue = self.game_zone_revenue - self.game_zone_error
        for revenue_value, ratio in kpi_ratio['game_zone']:
            if self.game_zone_revenue >= revenue_value:
                kpi_data['game_zone'] = (game_zone_revenue * ratio, ratio * 100)

        for revenue_value, ratio in kpi_ratio['vr']:
            if self.vr_revenue >= revenue_value:
                kpi_data['vr'] = (self.vr_revenue * ratio, ratio * 100)

        shift_salary += sum([kpi_data['bar'][0], kpi_data['game_zone'][0], kpi_data['vr'][0]])
        calculated_salary += sum([kpi_data['bar'][0], kpi_data['game_zone'][0], kpi_data['vr'][0]])
        kpi_data['shift_salary'] = shift_salary
        kpi_data['calculated_salary']= calculated_salary

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


class DisciplinaryRegulations(models.Model):
    article = models.CharField(max_length=10, verbose_name='Пункт')
    title = models.CharField(max_length=255, verbose_name='Наименование')
    base_penalty = models.FloatField(default=0.0, verbose_name='Сумма штрафа')
    sanction = models.CharField(max_length=255, verbose_name='Санкция', blank=True, null=True)

    class Meta:
        verbose_name = 'Пункт регламента'
        verbose_name_plural = 'Дисциплинарный регламент'

    def __str__(self) -> str:
        return f'{self.article} {self.title}'


class Publication(models.Model):
    author = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Автор публикации', related_name='author')
    publication_date = models.DateField(verbose_name='Дата публикации')
    link = models.TextField(verbose_name='Примечание (ссылка)', blank=True, null=True)
    auditor = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Аудитор', related_name='auditor')

    class Meta:
        verbose_name = 'Публикация'
        verbose_name_plural = 'Публикации'

    def __str__(self) -> str:
        return f'{self.publication_date} {self.author.get_full_name()}'
