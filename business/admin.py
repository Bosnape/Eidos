from django.contrib import admin
from .models import BusinessAccount, RegistrationSession, Service, Employee, PortfolioItem, Appointment
from customer.models import Customer

class BusinessAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone')
    search_fields = ('name', 'phone')
    
class RegistrationSessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'name', 'created_at')
    readonly_fields = ('created_at',)
    
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'price', 'available')
    search_fields = ('name', 'business__name')
    
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'phone')
    search_fields = ('name', 'business__name')

class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'business', 'created_at')
    search_fields = ('title', 'business__name')

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('service', 'business', 'date', 'time')
    search_fields = ('service__name', 'business__name')

admin.site.register(BusinessAccount, BusinessAccountAdmin)
admin.site.register(RegistrationSession, RegistrationSessionAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(Employee, EmployeeAdmin)
admin.site.register(PortfolioItem, PortfolioItemAdmin)
admin.site.register(Appointment, AppointmentAdmin)