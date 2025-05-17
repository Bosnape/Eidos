from django.urls import path
from . import views
from .views import get_available_hours

urlpatterns = [
    # Sign up
    path('signup/account-info/', views.registerBusinessInfo, name="register_IBusiness"),
    path('signup/account-credentials/', views.registerBusinessUser, name="register_UBusiness"),
    
    # Dashboard and manage profile
    path('dashboard/', views.provideDashboardSection, name="business_dashboard"),
    path('dashboard/manage-profile/', views.manageProfile, name="manage_profile"),
    
    # Manage services
    path('dashboard/services/', views.dashboardServicesView, name="dashboard_services"),
    path('dashboard/services/add-service/', views.addService, name='add_service'),
    path('dashboard/services/edit/<int:service_id>/', views.editService, name='edit_service'),
    path('dashboard/services/delete/<int:service_id>/', views.deleteService, name='delete_service'),
    
    # Manage social media
    path('dashboard/social-media/', views.updateSocialMedia, name='update_social_media'),
    
    # Manage employees
    path('dashboard/employees/', views.listEmployees, name="employee_list"),
    path('dashboard/employees/add/', views.addEmployee, name="add_employee"),

    # Manage portfolio
    path('dashboard/portfolio/', views.listPortfolio, name='portfolio_list'),
    path('dashboard/portfolio/add-work/', views.addPortfolio, name='add_portfolio'), 
    
    # Display business profile to the public 
    path('<str:business_name>/', views.displayProfile, name="business_profile"),

    # Manage schedules
    path('dashboard/schedules/', views.listSchedules, name='schedule_list'),
    path('dashboard/schedules/create/', views.createSchedule, name='create_schedule'),
    path('dashboard/schedules/<int:schedule_id>/edit/', views.editSchedule, name='edit_schedule'),
    path('dashboard/schedules/<int:schedule_id>/delete/', views.deleteSchedule, name='delete_schedule'),

    # Manage availability
    path('dashboard/availability/', views.manageAvailability, name='manage_availability'),
    path('dashboard/availability/<int:employee_id>/', views.manageAvailability, name='manage_availability'),

    # Staff calendar
    path('dashboard/calendar/', views.displayStaffCalendar, name='staff_calendar'),

    # Manage staff appointments
    path('dashboard/staff-appointments/', views.manageStaffAppointments, name='manage_staff_appointments'),
    path('dashboard/staff-appointments/create/', views.createStaffAppointment, name='create_staff_appointment'),
    path('dashboard/staff-appointments/<int:appointment_id>/edit/', views.editStaffAppointment, name='edit_staff_appointment'),
    path('dashboard/staff-appointments/<int:appointment_id>/delete/', views.deleteStaffAppointment, name='delete_staff_appointment'),
    path('api/get-available-hours/', get_available_hours, name='get_available_hours'),

    path('dashboard/staff-appointments/update-status/<int:appointment_id>/', 
         views.update_appointment_status, 
         name='update_appointment_status'),
]