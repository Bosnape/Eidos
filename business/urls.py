from django.urls import path
from . import views

urlpatterns = [
    # Sign up and login
    path('signup/account-info/', views.registerBusinessInfo, name="register_IBusiness"),
    path('signup/account-credentials/', views.registerBusinessUser, name="register_UBusiness"),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logoutBusiness, name='logout'),
    
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
    path('dashboard/employees/', views.listEmployee, name="employee_list"),
    path('dashboard/employees/add/', views.addEmployee, name="add_employee"),

    # Manage portfolio
    path('dashboard/portfolio/', views.listPortfolio, name='portfolio_list'),
    path('dashboard/portfolio/add-work/', views.addPortfolio, name='add_portfolio'), 
    
    # Display business profile to the public 
    path('<str:business_name>/', views.displayProfile, name="business_profile"),

    # Manage schedules
    path('dashboard/schedules/', views.schedule_list, name='schedule_list'),
    path('dashboard/schedules/create/', views.create_schedule, name='create_schedule'),
    path('dashboard/schedules/<int:schedule_id>/edit/', views.edit_schedule, name='edit_schedule'),
    path('dashboard/schedules/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),

    # Manage availability
    path('dashboard/availability/', views.manage_availability, name='manage_availability'),
    path('dashboard/availability/<int:employee_id>/', views.manage_availability, name='manage_availability'),

    # Staff calendar
    path('dashboard/calendar/', views.staff_calendar, name='staff_calendar'),

    # Manage staff appointments
    path('dashboard/staff-appointments/', views.manage_staff_appointments, name='manage_staff_appointments'),
    path('dashboard/staff-appointments/create/', views.create_staff_appointment, name='create_staff_appointment'),
    #path('dashboard/staff-appointments/<int:appointment_id>/edit/', views.edit_staff_appointment, name='edit_staff_appointment'),
    #path('dashboard/staff-appointments/<int:appointment_id>/delete/', views.delete_staff_appointment, name='delete_staff_appointment'),
]