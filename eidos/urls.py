from django.urls import path
from . import views

urlpatterns = [
    path('', views.showEidosHome, name="home"),
    path('contact/', views.showContactInfo, name="contact"), 
    path('business/', views.searchBusiness, name="search_business"),
]