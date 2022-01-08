from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


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


class Position(models.Model):
    title = models.CharField(max_length=255)
    name = models.CharField(max_length=60)
    position_salary = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'

    def __str__(self) -> str:
        return self.title