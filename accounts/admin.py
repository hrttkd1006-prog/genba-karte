from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, ContactMessage


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'workplace', 'is_hospital_admin', 'is_staff', 'date_joined']
    list_filter = ['is_hospital_admin', 'is_staff', 'is_active']
    search_fields = ['email', 'workplace']
    ordering = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('プロフィール', {'fields': ('workplace',)}),
        ('権限', {'fields': ('is_hospital_admin', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('日時', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'category', 'is_read', 'created_at']
    list_filter = ['is_read', 'category']
    search_fields = ['name', 'email', 'message']
    readonly_fields = ['name', 'email', 'category', 'message', 'created_at']
    ordering = ['-created_at']
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f'{queryset.count()}件を確認済みにしました。')
    mark_as_read.short_description = '確認済みにする'
