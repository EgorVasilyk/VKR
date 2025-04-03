from django.utils import timezone
from .models import Goals, Statuses
from django.db import transaction


def check_overdue_goals():
    """Периодическая задача для проверки просроченных целей"""
    overdue_status = Statuses.objects.filter(name='Просрочено').first()
    completed_status = Statuses.objects.filter(name='Выполнено').first()

    if not overdue_status or not completed_status:
        return

    with transaction.atomic():
        # Находим цели, которые просрочены и не выполнены
        overdue_goals = Goals.objects.filter(
            end_date__lt=timezone.now().date(),
            status__name__in=['В процессе', 'Новая']  # Или другие не завершенные статусы
        )

        for goal in overdue_goals:
            goal.status = overdue_status
            goal.save()