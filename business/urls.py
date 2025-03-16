from django.urls import path
from . import views

urlpatterns = [
    path('signup/account-info/', views.registerBusinessInfo, name="register_IBusiness"),
    path('signup/account-credentials/', views.registerBusinessUser, name="register_UBusiness"),
    path('login/', views.loginBusiness, name='login'),
    path('logout/', views.logoutBusiness, name='logout'),
    
    path('dashboard/', views.provideDashboardSection, name="business_dashboard"),
    path('dashboard/manage-profile', views.manageProfile, name="manage_profile"),
    path('dashboard/services', views.dashboardServicesView, name="dashboard_services"),
    path('dashboard/services/add-service/', views.addService, name='add_service'),
    path('dashboard/services/edit/<int:service_id>/', views.editService, name='edit_service'),
    path('dashboard/services/delete/<int:service_id>/', views.deleteService, name='delete_service'),
    path('dashboard/social-media/', views.updateSocialMedia, name='update_social_media'),

    path('<str:business_name>/', views.displayProfile, name="business_profile"),
]