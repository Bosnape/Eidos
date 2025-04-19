from django.urls import path
from . import views

urlpatterns = [
    # Sign up and login
    path('signup/account-info/', views.registerBusinessInfo, name="register_IBusiness"),
    path('signup/account-credentials/', views.registerBusinessUser, name="register_UBusiness"),
    path('login/', views.loginBusiness, name='login'),
    path('logout/', views.logoutBusiness, name='logout'),

    path('register/', views.register_choice, name='register_choice'),  # Elección cliente o negocio
    path('register/customer/', views.register_customer, name='register_customer'),  # Cliente
    
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

    # Appontment booking
    path('book-appointment/<int:business_id>/', views.book_appointment, name='book_appointment'),
    path('appointments/', views.userAppointments, name='userAppointments'),
]