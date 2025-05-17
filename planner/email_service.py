import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerificationCode
import logging

logger = logging.getLogger(__name__)


def send_verification_email(user, is_email_change=False):
    # Удаляем старые коды
    EmailVerificationCode.objects.filter(user=user).delete()

    # Генерируем новый код
    code = str(random.randint(1000, 9999))
    expires_at = timezone.now() + timedelta(minutes=15)

    # Сохраняем код
    EmailVerificationCode.objects.create(
        user=user,
        code=code,
        expires_at=expires_at
    )

    subject = 'Код подтверждения изменения email' if is_email_change else 'Код подтверждения регистрации'
    email_to = user.new_email if is_email_change else user.email

    send_mail(
        subject,
        f'Ваш код подтверждения: {code}\nКод действителен 15 минут.',
        settings.DEFAULT_FROM_EMAIL,
        [email_to],
        fail_silently=False,
    )
