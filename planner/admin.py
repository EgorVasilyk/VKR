from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied

from .models import *
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html


class AdminSite(admin.AdminSite):
    def has_permission(self, request):
        """Ограничиваем доступ только администраторам"""
        return super().has_permission(request) and \
            hasattr(request.user, 'role') and \
            request.user.role.name.lower() == 'admin'


custom_admin_site = AdminSite(name='custom_admin')


class IsDeletedFilter(admin.SimpleListFilter):
    title = 'Статус удаления'
    parameter_name = 'is_deleted'

    def lookups(self, request, model_admin):
        return (
            ('deleted', 'Удаленные'),
            ('active', 'Активные'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'deleted':
            return queryset.filter(is_deleted=True)
        if self.value() == 'active':
            return queryset.filter(is_deleted=False)


@admin.register(Users, site=custom_admin_site)
class AdminUsers(UserAdmin):
    list_display = ('username', 'role', 'is_staff', 'is_deleted')
    list_filter = ('role', 'is_deleted')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'role')}),
    )
    search_fields = ('username',)
    ordering = ('username',)
    actions = ['logical_delete', 'restore']

    def logical_delete(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, "Выбранные статусы помечены как удаленные")
    logical_delete.short_description = "Логически удалить"

    def restore(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, "Выбранные статусы восстановлены")
    restore.short_description = "Восстановить"

    def save_model(self, request, obj, form, change):
        if 'password' in form.changed_data:
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


@admin.register(Goals, site=custom_admin_site)
class AdminGoals(admin.ModelAdmin):
    list_display = ('user', 'title', 'type', 'status', 'is_deleted', 'admin_actions')
    list_filter = ('status', 'type', 'user', 'is_deleted')
    search_fields = ('title', 'user__username')
    actions = ['logical_delete', 'restore']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role.name.lower() == 'admin':
            return qs
        return qs.filter(user=request.user, is_deleted=False)

    def admin_actions(self, obj):
        links = []
        change_url = reverse('admin:planner_goals_change', args=[obj.id])
        delete_url = reverse('admin:planner_goals_delete', args=[obj.id])

        links.append(f'<a class="button" href="{change_url}">Изменить</a>')

        if not obj.is_deleted:
            links.append(f'<a class="button" href="{delete_url}">Удалить</a>')
        else:
            restore_url = reverse('admin:planner_goals_restore', args=[obj.id])
            links.append(f'<a class="button" href="{restore_url}">Восстановить</a>')

        return format_html('&nbsp;'.join(links))

    admin_actions.short_description = 'Действия'
    admin_actions.allow_tags = True

    def logical_delete(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, "Выбранные цели помечены как удаленные")
    logical_delete.short_description = "Логически удалить"

    def restore(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, "Выбранные цели восстановлены")
    restore.short_description = "Восстановить"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/restore/',
                 self.admin_site.admin_view(self.restore_view),
                 name='planner_goals_restore'),
        ]
        return custom_urls + urls

    def restore_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, Goals._meta, object_id)

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        obj.is_deleted = False
        obj.save()

        msg = f'Цель "{obj.title}" успешно восстановлена'
        self.message_user(request, msg, messages.SUCCESS)

        return HttpResponseRedirect(reverse('admin:planner_goals_changelist'))


admin.site.register(Goals, AdminGoals)


@admin.register(GoalItems, site=custom_admin_site)
class AdminGoalItems(admin.ModelAdmin):
    list_display = ('goal', 'title', 'status', 'is_deleted')
    list_filter = ('is_deleted',)
    actions = ['logical_delete', 'restore']

    def logical_delete(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, "Выбранные пункты цели помечены как удаленные")
    logical_delete.short_description = "Логически удалить"

    def restore(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, "Выбранные пункты цели восстановлены")
    restore.short_description = "Восстановить"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.role.name.lower() == 'admin':
            return qs
        return qs.filter(goal__user=request.user, is_deleted=False)


@admin.register(Roles, site=custom_admin_site)
class AdminRoles(admin.ModelAdmin):
    list_display = ('name', 'is_deleted')
    list_filter = ('is_deleted',)
    actions = ['logical_delete', 'restore']

    def logical_delete(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, "Выбранные роли помечены как удаленные")
    logical_delete.short_description = "Логически удалить"

    def restore(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, "Выбранные роли восстановлены")
    restore.short_description = "Восстановить"


@admin.register(Statuses, site=custom_admin_site)
class AdminStatuses(admin.ModelAdmin):
    list_display = ('name', 'is_deleted')
    list_filter = ('is_deleted',)
    actions = ['logical_delete', 'restore']

    def logical_delete(self, request, queryset):
        queryset.update(is_deleted=True)
        self.message_user(request, "Выбранные статусы помечены как удаленные")
    logical_delete.short_description = "Логически удалить"

    def restore(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(request, "Выбранные статусы восстановлены")
    restore.short_description = "Восстановить"


# Переопределяем стандартную админку
admin.site = custom_admin_site
admin.site.site_header = "Администрирование системы целей"
admin.site.site_title = "Система целей"
admin.site.index_title = "Панель управления"
