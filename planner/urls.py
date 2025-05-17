from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('register/', views.register, name='register'),
    path('', views.user_login, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('goal-edit/', views.goal_edit, name='goal_edit'),
    path('goal-edit/<int:goal_id>/', views.goal_edit, name='goal_edit'),  # Для редактирования
    path('goal-delete/<int:goal_id>/', views.goal_delete, name='goal_delete'),
    path('goal/<int:goal_id>/item/', views.goal_item_edit, name='goal_item_edit'),
    path('goal/<int:goal_id>/item/<int:item_id>/', views.goal_item_edit, name='goal_item_edit'),
    path('goal/<int:goal_id>/item/<int:item_id>/delete/', views.goal_item_delete, name='goal_item_delete'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/reset/', views.reset_profile, name='reset_profile'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('goals/<str:date_str>/', views.day_goals, name='day_goals'),
    path('admin/planner/goals/<int:pk>/recover/', views.recover_goal, name='planner_goals_recover'),
    path('reschedule-goal/', views.reschedule_goal, name='reschedule_goal'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-code/', views.resend_verification_code, name='resend_verification_code'),
    path('profile/verify-email-change/', views.verify_email_change, name='verify_email_change'),
    path('profile/resend-email-change-code/', views.resend_email_change_code, name='resend_email_change_code'),
    path('profile/notifications/', views.notification_settings, name='notification_settings'),
]
