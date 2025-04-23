from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.showEidosHome, name="home"),
    path('contact/', views.showContactInfo, name="contact"), 
    path('business/', views.searchBusiness, name="search_business"),
    path('register/choice/', views.register_choice, name='register_choice'),
    path('business/', include('business.urls')),  
    path('customer/', include('customer.urls')),


]