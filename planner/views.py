from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash
from .forms import *
from .models import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Case, When, Value, IntegerField, Count
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from datetime import timedelta, date, datetime
from calendar import monthrange, HTMLCalendar
from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from .email_service import send_verification_email
from smtplib import SMTPAuthenticationError
import smtplib
from django.views.decorators.debug import sensitive_variables


@sensitive_variables('password')
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_active = False
                user.save()

                try:
                    send_verification_email(user)
                    # Сохраняем email в сессии для неавторизованного доступа
                    request.session['verify_email'] = user.email
                    return redirect('verify_email')
                except smtplib.SMTPException as e:
                    print(f"SMTP error: {e}")
                    messages.error(request, 'Ошибка отправки email. Пожалуйста, попробуйте позже.')
                    return render(request, 'planner/register.html', {'form': form})

            except Exception as e:
                print(f"General error: {e}")
                messages.error(request, 'Ошибка регистрации')
    else:
        form = RegistrationForm()
    return render(request, 'planner/register.html', {'form': form})


def verify_email(request):
    # Проверяем email в сессии
    verify_email = request.session.get('verify_email')

    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            # Ищем пользователя по email из сессии или по авторизации
            if verify_email:
                user = Users.objects.get(email=verify_email)
            elif request.user.is_authenticated:
                user = request.user
            else:
                messages.error(request, 'Сессия истекла. Пожалуйста, зарегистрируйтесь снова.')
                return redirect('register')

            verification = EmailVerificationCode.objects.get(
                user=user,
                code=code,
                expires_at__gte=timezone.now()
            )

            user.is_email_verified = True
            user.is_active = True
            user.save()
            verification.delete()

            # Очищаем сессию после успешной верификации
            if 'verify_email' in request.session:
                del request.session['verify_email']

            login(request, user)
            return redirect('calendar')

        except (EmailVerificationCode.DoesNotExist, Users.DoesNotExist):
            messages.error(request, 'Неверный или просроченный код')

    return render(request, 'planner/verify_email.html')


def resend_verification_code(request):
    # Проверяем, есть ли email в сессии (для неавторизованных пользователей)
    verify_email = request.session.get('verify_email')

    if verify_email:
        try:
            user = Users.objects.get(email=verify_email)
            send_verification_email(user)
            messages.success(request, 'Новый код подтверждения отправлен на ваш email')
        except Users.DoesNotExist:
            messages.error(request, 'Пользователь не найден')
            return redirect('register')
        except Exception as e:
            messages.error(request, f'Ошибка отправки: {str(e)}')
    elif request.user.is_authenticated and not request.user.is_email_verified:
        try:
            send_verification_email(request.user)
            messages.success(request, 'Новый код подтверждения отправлен на ваш email')
        except Exception as e:
            messages.error(request, f'Ошибка отправки: {str(e)}')
    else:
        messages.warning(request, 'Ваш email уже подтверждён или сессия истекла')

    return redirect('verify_email')


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('calendar')  # Переход на главную страницу
    else:
        form = LoginForm()
    return render(request, 'planner/login.html', {'form': form})


@login_required
def home(request):
    # Проверяем просроченные цели перед отображением
    Goals.check_overdue_goals_for_user(request.user)
    # Получаем выбранный тип из GET-параметра
    selected_type = request.GET.get('type')

    # Основной запрос с фильтрацией
    goals = Goals.objects.filter(user=request.user, is_deleted=False)
    # Добавляем prefetch_related с фильтром для пунктов целей
    goals = goals.prefetch_related(
        models.Prefetch(
            'goalitems_set',
            queryset=GoalItems.objects.filter(is_deleted=False),
            to_attr='active_items'
        )
    )

    # Применяем фильтрацию
    if selected_type and selected_type != 'all':
        goals = goals.filter(type=selected_type)

    # Получаем уникальные типы для фильтра
    goal_types = Goals.objects.filter(user=request.user, is_deleted=False) \
        .exclude(type__isnull=True) \
        .exclude(type__exact='') \
        .values('type') \
        .annotate(count=Count('id')) \
        .order_by('type')

    selected_type = request.GET.get('type')
    if selected_type and selected_type != 'all':
        goals = goals.filter(type=selected_type)

    goal_types = Goals.objects.filter(user=request.user, is_deleted=False) \
        .exclude(type__isnull=True) \
        .exclude(type__exact='') \
        .values('type') \
        .annotate(count=Count('id')) \
        .order_by('type')

    # Создаем порядок сортировки по статусам
    status_order = Case(
        When(status__name='Просрочено', then=Value(1)),
        When(status__name='В процессе', then=Value(2)),
        When(status__name='Выполнено', then=Value(3)),
        default=Value(4),
        output_field=IntegerField()
    )

    # Сортируем цели сначала по статусу, затем по дате начала (новые сначала)
    goals = goals.annotate(
        status_order=status_order
    ).order_by('status_order')

    return render(request, 'planner/home.html', {
        'goals': goals,
        'goal_types': goal_types,
        'selected_type': selected_type
    })


@login_required
def goal_edit(request, goal_id=None):
    if goal_id:
        goal = get_object_or_404(Goals, id=goal_id, user=request.user, is_deleted=False)
        old_status = goal.status.name if goal.status else None
    else:
        goal = Goals(user=request.user)
        old_status = None

    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            new_goal = form.save()
            new_status = new_goal.status.name if new_goal.status else None

            # Проверяем изменение статуса на "Выполнено"
            if old_status == 'Выполнено' and new_status != 'Выполнено':
                request.user.rank = max(1, request.user.rank - 1)
                request.user.save()
            elif new_status == 'Выполнено' and old_status != 'Выполнено':
                request.user.rank += 1
                request.user.save()

            return redirect('home')
    else:
        form = GoalForm(instance=goal)

    statuses = Statuses.objects.filter(is_deleted=False)
    items = goal.goalitems_set.filter(is_deleted=False) if goal.pk else []

    return render(request, 'planner/goal_edit.html', {
        'form': form,
        'goal': goal,
        'items': items,
        'statuses': statuses
    })


@login_required
def goal_delete(request, goal_id):
    if request.method == 'POST':
        goal = get_object_or_404(Goals, id=goal_id, user=request.user)
        goal.delete()
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def goal_item_edit(request, goal_id, item_id=None):
    goal = get_object_or_404(Goals, pk=goal_id, user=request.user)  # Добавлена проверка пользователя
    if item_id:
        item = get_object_or_404(GoalItems, pk=item_id, goal=goal)
    else:
        item = GoalItems(goal=goal)

    if request.method == 'POST':
        form = GoalItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            # Получаем обновленный объект цели
            goal = Goals.objects.get(pk=goal_id)
            # Проверяем и обновляем статус цели
            goal.check_and_update_status()
            return redirect('goal_edit', goal_id=goal.id)
    else:
        form = GoalItemForm(instance=item)

    # Получаем все доступные статусы
    statuses = Statuses.objects.filter(is_deleted=False)

    return render(request, 'planner/goal_item_edit.html', {
        'form': form,
        'goal': goal,
        'item': item,
        'statuses': statuses  # Добавляем статусы в контекст
    })


@login_required
def goal_item_delete(request, goal_id, item_id):
    item = get_object_or_404(GoalItems, pk=item_id, goal_id=goal_id, goal__user=request.user)
    item.delete()
    return redirect('goal_edit', goal_id=goal_id)


@login_required
def profile(request):
    return render(request, 'planner/profile.html')


@login_required
def edit_profile(request):
    email_change_form = EmailChangeForm()

    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=request.user)
        password_form = PasswordChangeForm(request.user, request.POST)

        if 'username_submit' in request.POST and user_form.is_valid():
            user_form.save()
            messages.success(request, 'Профиль успешно обновлен')
            return redirect('profile')

        elif 'password_submit' in request.POST and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен')
            return redirect('profile')

        elif 'email_submit' in request.POST:
            email_change_form = EmailChangeForm(request.POST)
            if email_change_form.is_valid():
                # Сохраняем новый email во временное поле
                request.user.new_email = email_change_form.cleaned_data['new_email']
                request.user.save()

                # Отправляем код подтверждения
                send_verification_email(request.user, is_email_change=True)
                messages.info(request, 'Код подтверждения отправлен на новый email')
                return redirect('verify_email_change')

    else:
        user_form = UserEditForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    return render(request, 'planner/edit_profile.html', {
        'user_form': user_form,
        'password_form': password_form,
        'email_change_form': email_change_form,
    })


@login_required
def verify_email_change(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            verification = EmailVerificationCode.objects.get(
                user=request.user,
                code=code,
                expires_at__gte=timezone.now()
            )

            # Применяем изменение email
            request.user.email = request.user.new_email
            request.user.new_email = None
            request.user.is_email_verified = True
            request.user.save()

            verification.delete()
            messages.success(request, 'Email успешно изменен')
            return redirect('profile')

        except EmailVerificationCode.DoesNotExist:
            messages.error(request, 'Неверный или просроченный код')

    return render(request, 'planner/verify_email_change.html')


@login_required
def resend_email_change_code(request):
    if hasattr(request.user, 'new_email') and request.user.new_email:
        try:
            send_verification_email(request.user, is_email_change=True)
            messages.success(request, 'Новый код подтверждения отправлен')
        except Exception as e:
            messages.error(request, f'Ошибка отправки: {str(e)}')
    else:
        messages.error(request, 'Не указан новый email для подтверждения')

    return redirect('verify_email_change')


@login_required
def reset_profile(request):
    if request.method == 'POST':
        # Удаляем все цели пользователя
        Goals.objects.filter(user=request.user).delete()
        # Сбрасываем уровень
        request.user.rank = 0
        request.user.save()
        messages.success(request, 'Профиль успешно сброшен')
        return redirect('profile')

    return render(request, 'planner/reset_confirm.html')


@login_required
def calendar_view(request):
    # Получаем текущую дату или выбранный месяц из параметров
    month_param = request.GET.get('month')
    date_param = request.GET.get('date')

    if month_param:
        year, month = map(int, month_param.split('-'))
        current_date = date(year, month, 1)
    else:
        current_date = timezone.now().date()

    if date_param:
        selected_date = date(*map(int, date_param.split('-')))
    else:
        selected_date = timezone.now().date()

    # Навигационные даты
    prev_month = (current_date - timedelta(days=1)).replace(day=1)
    next_month = (current_date + timedelta(days=32)).replace(day=1)

    # Получаем количество дней в месяце и день недели первого дня
    _, num_days = monthrange(current_date.year, current_date.month)
    first_day = date(current_date.year, current_date.month, 1).weekday()

    # Подготавливаем данные для дней
    calendar_days = []
    today = timezone.now().date()

    # Пустые ячейки для дней предыдущего месяца
    for _ in range(first_day):
        calendar_days.append({
            'day': '',
            'is_current_month': False,
            'is_today': False,
            'goals_count': 0,
            'date': None
        })

    # Дни текущего месяца
    for day in range(1, num_days + 1):
        current_day = date(current_date.year, current_date.month, day)
        goals_count = Goals.objects.filter(
            models.Q(start_date__lte=current_day, end_date__gte=current_day) |
            models.Q(deadline=current_day),
            is_deleted=False,  # Добавьте эту фильтрацию
            user=request.user  # Или другая логика доступа
        ).count()

        calendar_days.append({
            'day': day,
            'is_current_month': True,
            'is_today': current_day == today,
            'goals_count': goals_count,
            'date': current_day
        })

    # Пустые ячейки для завершения сетки (до 42 ячеек)
    while len(calendar_days) % 7 != 0 or len(calendar_days) < 42:
        calendar_days.append({
            'day': '',
            'is_current_month': False,
            'is_today': False,
            'goals_count': 0,
            'date': None
        })

    context = {
        'current_month': current_date.strftime('%B'),
        'current_year': current_date.year,
        'calendar_days': calendar_days,
        'prev_month': prev_month,
        'next_month': next_month,
    }

    return render(request, 'planner/calendar.html', context)


def day_goals(request, date_str):
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        current_date = timezone.now().date()

    prev_day = current_date - timedelta(days=1)
    next_day = current_date + timedelta(days=1)

    goals = Goals.objects.filter(
        models.Q(start_date__lte=current_date, end_date__gte=current_date) |
        models.Q(deadline=current_date),
        is_deleted=False,  # Фильтрация удалённых
        user=request.user  # Или другая логика доступа
    ).prefetch_related(
        models.Prefetch(
            'goalitems_set',
            queryset=GoalItems.objects.filter(is_deleted=False),
            to_attr='active_items'
        )
    ).select_related('status')

    context = {
        'current_date': current_date,
        'prev_day': prev_day,
        'next_day': next_day,
        'goals': goals,
    }
    return render(request, 'planner/day_goals.html', context)


@login_required
def recover_goal(request, pk):
    if request.user.role.name.lower() != 'admin':
        raise PermissionDenied
    goal = get_object_or_404(Goals, pk=pk)
    goal.is_deleted = False
    goal.save()
    return redirect('admin:planner_goals_changelist')


@login_required
def reschedule_goal(request):
    if request.method == 'POST':
        goal_id = request.POST.get('goal_id')
        new_end_date_str = request.POST.get('new_end_date')

        try:
            goal = Goals.objects.get(id=goal_id, user=request.user)
            new_end_date = datetime.strptime(new_end_date_str, '%Y-%m-%d').date()

            # Проверка что новая дата позже даты начала
            if goal.start_date and new_end_date <= goal.start_date:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Дата завершения должна быть позже даты начала'
                }, status=400)

            # Проверка что новая дата в будущем
            if new_end_date <= timezone.now().date():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Новая дата должна быть в будущем'
                }, status=400)

            goal.end_date = new_end_date

            # Если цель была просрочена, меняем статус на "В процессе"
            if goal.status.name == 'Просрочено':
                in_progress_status = Statuses.objects.get(name='В процессе')
                goal.status = in_progress_status

            goal.save()
            return JsonResponse({'status': 'success'})

        except Goals.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Цель не найдена'
            }, status=404)
        except Statuses.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Статус "В процессе" не найден'
            }, status=500)
        except ValueError:
            return JsonResponse({
                'status': 'error',
                'message': 'Неверный формат даты'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Неверный метод запроса'
    }, status=400)

@login_required
def notification_settings(request):
    try:
        settings = request.user.notification_settings
    except NotificationSettings.DoesNotExist:
        settings = NotificationSettings.objects.create(user=request.user)

    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки уведомлений сохранены')
            return redirect('notification_settings')
    else:
        form = NotificationSettingsForm(instance=settings)

    return render(request, 'planner/notification_settings.html', {
        'form': form
    })
