from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    birth_date = models.DateField(null=True, verbose_name='Дата рождения')
    employment_date = models.DateField(null=True, verbose_name='Дата трудоустройства')
    position = models.ForeignKey('Position', on_delete=models.PROTECT, null=True)
    attestation = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.user.username

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            instance.profile = Profile.objects.create(user=instance)
        instance.profile.save()

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()


class WorkingShift(models.Model):
    hall_admin = models.ForeignKey(User, on_delete=models.PROTECT, related_name='hall_admin')
    cash_admin = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cash_admin')
    shift_date = models.DateField()
    bar_revenue = models.FloatField()
    game_zone_revenue = models.FloatField()
    vr_revenue = models.FloatField()
    hall_cleaning = models.BooleanField(default=True)
    hall_admin_discipline = models.BooleanField(default=True)
    cach_admin_discipline = models.BooleanField(default=True)
    shortage = models.FloatField(default=0)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Смена'
        verbose_name_plural = 'Смены'


class Position(models.Model):
    title = models.CharField(max_length=255)
    position_salary = models.FloatField(null=True)

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'

    def __str__(self) -> str:
        return self.title