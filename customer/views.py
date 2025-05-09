import datetime
from datetime import date
from django.contrib import messages
from django.contrib.auth import get_user_model, login 
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import CustomerUserForm, AppointmentForm
from .models import Customer
from business.models import Service, BusinessAccount, Employee, Appointment
from business.utils import get_available_times  # al inicio del archivo
from business.utils import create_appointment  # al inicio también

# Customer registration
def registerCustomer(request):
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

            login(request, user)
            return redirect('userAppointments')
    else:
        form = CustomerUserForm()

    return render(request, 'register_customer.html', {'form': form})

# Client Appointment View
@login_required
def listUserAppointments(request):

    if not hasattr(request.user, 'customer'):
        return render(request, 'error.html', {'message': 'Only clients can view appointments.'})

    customer = request.user.customer
    # Use the ForeignKey relationship instead of filtering by email
    appointments = Appointment.objects.filter(customer=customer)
    
    # If there are no appointments with the direct relationship, search by email as an alternative
    if not appointments.exists():
        appointments = Appointment.objects.filter(customer_email=customer.user.email)

    return render(request, 'user_appointments.html', {'appointments': appointments})

today = date.today().isoformat()
# View to book an appointment
@login_required(login_url='must_be_logged_in')
def bookAppointment(request, business_id):
    
    try:
        business = BusinessAccount.objects.get(id=business_id)
    except BusinessAccount.DoesNotExist:
        return render(request, 'error.html', {'message': 'Business not found'})  

    services = Service.objects.filter(business=business)  # Obtain the services associated with the business
    barbers = business.employees.all()

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            if not hasattr(request.user, 'customer'):
                messages.error(request, "Your account is not registered as a customer.")
                return redirect('home')

            customer = request.user.customer
            try:
                create_appointment(form, business, customer=customer)  # we use de centralized function
                messages.success(request, "Appointment booked successfully.")
                return redirect('userAppointments')
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AppointmentForm()
        form.fields['service'].queryset = services
        form.fields['barber'].queryset = barbers

    return render(request, 'book_appointment.html', {
        'form': form,
        'business': business,
        'services': services,  # Pass the services to the template
        'barbers': barbers,
        'today': today, 
    })


# View for unauthenticated users
def must_be_logged_in(request):
    return render(request, 'must_be_logged_in.html')

# View to cancel an appointment
@require_POST
@login_required
def cancelAppointment(request, appointment_id):
    try:
        appointment = Appointment.objects.get(id=appointment_id, customer_email=request.user.email)
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, "Appointment cancelled successfully.")
    except Appointment.DoesNotExist:
        messages.error(request, "Appointment not found or unauthorized.")

    return redirect('userAppointments')