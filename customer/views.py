from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages

from .models import Customer
from business.models import Service
from .forms import CustomerUserForm, AppointmentForm

# Para mostrar la vista de elección de registro
def register_choice(request):
    return render(request, 'register_choice.html')

# Registro para clientes
def register_customer(request):
    Account = get_user_model()

    if request.method == 'POST':
        form = CustomerUserForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            user = Account.objects.create_user(email=email, password=password)
            
            user.is_customer = True
            user.save()

            customer = Customer.objects.create(
                user=user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                identification=form.cleaned_data['identification']
            )

            return redirect('login')
    else:
        form = CustomerUserForm()

    return render(request, 'register_customer.html', {'form': form})

# Para mostrar el listado de citas del cliente
@login_required
def userAppointments(request):
    from business.models import Appointment  # Import local para evitar un ciclo de imports

    appointments = []  # Temporal, para evitar error.
    return render(request, 'user_appointments.html', {'appointments': appointments})

# Para mostrar la vista de reserva de citas
def book_appointment(request, business_id):
    from business.models import BusinessAccount
    
    try:
        business = BusinessAccount.objects.get(id=business_id)
    except BusinessAccount.DoesNotExist:
        return render(request, 'error.html', {'message': 'Business not found'})  

    services = Service.objects.filter(business=business)  # Obtener los servicios asociados al negocio

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.business = business
            appointment.customer = request.user.customer
            appointment.service = form.cleaned_data['service'] 
            appointment.price = appointment.service.price 
            appointment.customer_satisfaction = 3 #Temporal
            appointment.repeat_customer = False #Temporal
            appointment.no_show = False #Temporal
            appointment.save()
            return redirect('userAppointments')
    else:
        form = AppointmentForm()
        form.fields['service'].queryset = services  # Filtrar los servicios en el formulario

    return render(request, 'book_appointment.html', {
        'form': form,
        'business': business,
        'services': services,  # Pasar los servicios al template
    })