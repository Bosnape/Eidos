from django.contrib import admin
from .models import BusinessAccount, RegistrationSession, Service

class BusinessAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone')
    search_fields = ('name', 'phone')
    
class RegistrationSessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'name', 'created_at')
    readonly_fields = ('created_at',)
    
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'price', 'available')
    search_fields = ('name', 'business__name')

admin.site.register(BusinessAccount, BusinessAccountAdmin)
admin.site.register(RegistrationSession, RegistrationSessionAdmin)
admin.site.register(Service, ServiceAdmin)