from django.urls import path
from . import views

urlpatterns = [
    path('signup/account-info/', views.registerBusinessInfo, name="register_IBusiness"),
    path('signup/account-credentials/', views.registerBusinessUser, name="register_UBusiness"),
    path('login/', views.loginBusiness, name='login'),
    path('logout/', views.logoutBusiness, name='logout'),
    path('dashboard/', views.provideDashboardSection, name="business_dashboard"),
    path('dashboard/services', views.provideServicesSection, name="business_services"),
    path('dashboard/manage-profile', views.manageProfile, name="manage_profile"),
    path('<str:business_name>/', views.displayProfile, name="business_profile"),
]