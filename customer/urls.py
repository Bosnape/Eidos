from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.registerChoice, name='register_choice'),  # Elección cliente o negocio
    path('register/customer/', views.registerCustomer, name='register_customer'),  # Cliente

    # Appontment booking
    path('book-appointment/<int:business_id>/', views.bookAppointment, name='book_appointment'),
    path('appointments/', views.listUserAppointments, name='userAppointments'),

    #Must be logged in
    path('must-be-logged-in/', views.must_be_logged_in, name='must_be_logged_in'),

    #Appointment Management
    path('cancel-appointment/<int:appointment_id>/', views.cancelAppointment, name='cancel_appointment'),
]