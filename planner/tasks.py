from celery.loaders import app
from .models import *
from django.db import transaction
from django.template.loader import render_to_string
from celery.schedules import crontab
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, date, timedelta
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from background_task import background


@shared_task
def send_daily_reminders_task():
    send_daily_reminders()


app.conf.beat_schedule = {
    'send-daily-reminders': {
        'task': 'planner.tasks.send_daily_reminders',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
    },
}


@background(schedule=60)  # Проверка каждые 60 секунд
def send_daily_reminders():
    today = date.today()
    now = timezone.localtime(timezone.now())
    current_time = now.time()

    users = Users.objects.filter(
        notification_settings__daily_reminder=True,
        is_active=True,
        is_email_verified=True
    ).select_related('notification_settings')

    for user in users:
        settings = user.notification_settings

        if settings.last_sent and settings.last_sent.date() == today:
            continue

        send_time = settings.send_time
        if current_time < send_time:
            continue

        goals = Goals.objects.filter(
            Q(user=user, is_deleted=False) &
            (Q(start_date__lte=today, end_date__gte=today) | Q(deadline=today))
        ).prefetch_related('goalitems_set')

        if goals.exists():
            subject = f'Ваши цели на {today.strftime("%d.%m.%Y")}'
            html_content = render_to_string('planner/email/daily_reminder.html', {
                'user': user,
                'goals': goals,
                'date': today,
            })

            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body="Просмотрите HTML-версию письма",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()

                NotificationSettings.objects.filter(pk=settings.pk).update(
                    last_sent=now
                )
            except Exception as e:
                print(f"Ошибка отправки для {user.email}: {str(e)}")


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