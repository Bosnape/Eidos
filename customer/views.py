from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages

from .models import Customer
from business.models import Service
from .forms import CustomerUserForm, AppointmentForm
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect
from django.urls import reverse

# View to choose record type
def register_choice(request):
    return render(request, 'register_choice.html')

# Customer registration
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

            Customer.objects.create(
                user=user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                identification=form.cleaned_data['identification']
            )

            return redirect('login')
    else:
        form = CustomerUserForm()

    return render(request, 'register_customer.html', {'form': form})

# Client Appointment View
@login_required
def userAppointments(request):
    from business.models import Appointment

    if not hasattr(request.user, 'customer'):
        return render(request, 'error.html', {'message': 'Solo los clientes pueden ver sus citas.'})

    customer = request.user.customer
    appointments = Appointment.objects.filter(customer_email=customer.user.email)

    return render(request, 'user_appointments.html', {'appointments': appointments})

# View to book an appointment
@login_required(login_url='must_be_logged_in')
def book_appointment(request, business_id):
    from business.models import BusinessAccount

    try:
        business = BusinessAccount.objects.get(id=business_id)
    except BusinessAccount.DoesNotExist:
        return render(request, 'error.html', {'message': 'Business not found'})  

    services = Service.objects.filter(business=business)  # Obtain the services associated with the business

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.business = business

            # Check if the user has an associated client
            if not hasattr(request.user, 'customer'):
                messages.error(request, "Tu cuenta no está registrada como cliente.")
                return redirect('home')  # Redirects to the home page if there is no client associated

            customer = request.user.customer
            appointment.customer_name = f"{customer.first_name} {customer.last_name}"
            appointment.customer_email = customer.user.email

            appointment.service = form.cleaned_data['service']
            appointment.price = appointment.service.price
            appointment.customer_satisfaction = 3  # Temporal
            appointment.repeat_customer = False    # Temporal
            appointment.no_show = False            # Temporal
            appointment.save()
            return redirect('userAppointments')
    else:
        form = AppointmentForm()
        form.fields['service'].queryset = services  # Filter the services in the form

    return render(request, 'book_appointment.html', {
        'form': form,
        'business': business,
        'services': services,  # Pass the services to the template
    })

# View for unauthenticated users
def must_be_logged_in(request):
    return render(request, 'must_be_logged_in.html')


# View to cancel an appointment
@require_POST
@login_required
def cancel_appointment(request, appointment_id):
    from business.models import Appointment

    try:
        appointment = Appointment.objects.get(id=appointment_id, customer_email=request.user.email)
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, "Appointment cancelled successfully.")
    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found or unauthorized.")

    return redirect('userAppointments')