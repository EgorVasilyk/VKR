# from django.apps import AppConfig
#
#
# class PlannerConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'planner'
#
#     def ready(self):
#         from .tasks import send_daily_reminders
#         # Запускаем задачу при старте приложения
#         send_daily_reminders(repeat=60)  # Повтор каждые 60 секунд
