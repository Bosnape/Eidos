from django.contrib import admin
from .models import BusinessAccount, RegistrationSession

class BusinessAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone')
    search_fields = ('name', 'phone')
    
class RegistrationSessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'name', 'created_at')
    readonly_fields = ('created_at',)

admin.site.register(BusinessAccount, BusinessAccountAdmin)
admin.site.register(RegistrationSession, RegistrationSessionAdmin)