from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_choice, name='register_choice'),  # Elección cliente o negocio
    path('register/customer/', views.register_customer, name='register_customer'),  # Cliente

    # Appontment booking
    path('book-appointment/<int:business_id>/', views.book_appointment, name='book_appointment'),
    path('appointments/', views.userAppointments, name='userAppointments'),
]