from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'is_staff', 'date_joined')
    search_fields = ('email',)
    readonly_fields = ('date_joined',)
    ordering = ('email',)
    
    filter_horizontal = ()
    list_filter = ()
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

admin.site.register(Account, CustomUserAdmin)