from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils import timezone


class GoalItems(models.Model):
    goal = models.ForeignKey('Goals', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    status = models.ForeignKey('Statuses', models.DO_NOTHING)
    is_deleted = models.BooleanField(default=False, verbose_name="Удалено")

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    class Meta:
        managed = False
        db_table = 'goal_items'


class Goals(models.Model):
    user = models.ForeignKey('Users', models.DO_NOTHING)
    title = models.CharField(max_length=100)
    type = models.CharField(max_length=50, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    status = models.ForeignKey('Statuses', models.DO_NOTHING)
    is_deleted = models.BooleanField(default=False, verbose_name="Удалено")

    def is_overdue(self):
        """Проверяет, просрочена ли цель (дата завершения раньше текущей даты)"""
        if self.end_date:
            return self.end_date < timezone.now().date()
        return False

    def update_status(self, new_status):
        """
        Безопасное обновление статуса без рекурсии
        Args:
            new_status (Statuses): Новый статус для установки
        """
        if self.status_id != new_status.id:
            old_status = self.status
            self.status = new_status
            # Сохраняем только поле статуса, избегая полного save()
            super(Goals, self).save(update_fields=['status'])

            # Обновляем ранг пользователя при изменении статуса "Выполнено"
            if old_status and old_status.name == 'Выполнено' and new_status.name != 'Выполнено':
                self.user.rank = max(1, self.user.rank - 1)
                self.user.save(update_fields=['rank'])
            elif new_status.name == 'Выполнено' and (not old_status or old_status.name != 'Выполнено'):
                self.user.rank += 1
                self.user.save(update_fields=['rank'])

    def check_and_update_status(self):
        """Проверяет и обновляет статус цели, избегая рекурсии"""
        # Получаем необходимые статусы один раз
        completed_status = Statuses.objects.filter(name='Выполнено').first()
        overdue_status = Statuses.objects.filter(name='Просрочено').first()

        if not completed_status or not overdue_status:
            return

        # Если цель уже выполнена - ничего не делаем
        if self.status == completed_status:
            return

        # Проверяем просроченность
        if self.is_overdue():
            if self.status != overdue_status:
                self.update_status(overdue_status)
            return

        # Проверяем выполнение всех пунктов (только для не просроченных целей)
        items = self.goalitems_set.all()
        if items.count() > 0 and all(item.status.name == 'Выполнено' for item in items):
            if self.status != completed_status:
                self.update_status(completed_status)

    def save(self, *args, **kwargs):
        """
        Переопределенный метод save с проверкой на создание/обновление
        Args:
            *args: Аргументы
            **kwargs: Ключевые аргументы
        """
        creating = not self.pk
        super(Goals, self).save(*args, **kwargs)

        # Проверяем статус только при обновлении существующей цели
        if not creating:
            self.check_and_update_status()

    @classmethod
    def check_overdue_goals_for_user(cls, user):
        """
        Проверяет и обновляет просроченные цели для конкретного пользователя
        Args:
            user (Users): Пользователь, чьи цели нужно проверить
        """
        overdue_status = Statuses.objects.filter(name='Просрочено').first()
        if not overdue_status:
            return

        today = timezone.now().date()

        # Находим цели, которые просрочены и не имеют статуса "Выполнено" или "Просрочено"
        overdue_goals = cls.objects.filter(
            user=user,
            end_date__lt=today
        ).exclude(
            status__name__in=['Выполнено', 'Просрочено']
        )

        for goal in overdue_goals:
            goal.update_status(overdue_status)

    class Meta:
        managed = False
        db_table = 'goals'

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()


@receiver(post_save, sender='planner.GoalItems')
def update_goal_status_on_item_change(sender, instance, **kwargs):
    """
    Сигнал для обновления статуса цели при изменении пункта
    Args:
        sender: Модель-отправитель
        instance: Экземпляр GoalItems
        **kwargs: Дополнительные аргументы
    """
    instance.goal.check_and_update_status()


class Roles(models.Model):
    name = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'roles'


class Statuses(models.Model):
    name = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = 'statuses'


class Users(AbstractUser):
    role = models.ForeignKey('Roles', on_delete=models.CASCADE, related_name='users', default=1)
    password = models.CharField(max_length=128, db_column='password_hash')
    rank = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def save(self, *args, **kwargs):
        self.rank = max(1, self.rank)  # Гарантируем, что уровень не меньше 1
        super().save(*args, **kwargs)

    @property
    def progress_percentage(self):
        return min(self.rank * 5, 100)  # 10% за каждую цель, максимум 100%

    def get_level_name(self):
        levels = {
            1: 'Новичок',
            2: 'Опытный',
            3: 'Продвинутый',
            4: 'Эксперт'
        }
        level = min((self.rank // 5) + 1, 4)  # Новый уровень каждые 5 целей
        return levels.get(level, 'Новичок')

    class Meta:
        managed = True
        db_table = 'users'
