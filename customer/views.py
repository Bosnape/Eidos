import datetime

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
from business.models import Service, BusinessAccount, Employee, Shift, Availability
from business.utils import get_available_times  # al inicio del archivo
from business.utils import create_appointment  # al inicio también



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

            login(request, user)
            return redirect('userAppointments')
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
    # Usar la relación ForeignKey en lugar de filtrar por email
    appointments = Appointment.objects.filter(customer=customer)
    
    # Si no hay citas con la relación directa, buscar por email como fallback
    if not appointments.exists():
        appointments = Appointment.objects.filter(customer_email=customer.user.email)

    return render(request, 'user_appointments.html', {'appointments': appointments})


# View to book an appointment
@login_required(login_url='must_be_logged_in')
def book_appointment(request, business_id):
    
    try:
        business = BusinessAccount.objects.get(id=business_id)
    except BusinessAccount.DoesNotExist:
        return render(request, 'error.html', {'message': 'Business not found'})  

    services = Service.objects.filter(business=business)
    employees = Employee.objects.filter(business=business)
    
    # Para AJAX: si se solicitan horarios disponibles
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'employee_id' in request.GET and 'date' in request.GET:
        employee_id = request.GET.get('employee_id')
        date_str = request.GET.get('date')

        try:
            employee = Employee.objects.get(id=employee_id)
            selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

            available_times, msg = get_available_times(employee, selected_date)
            if msg:
                return JsonResponse({'available_times': [], 'message': msg})
            return JsonResponse({'available_times': available_times})

        except (Employee.DoesNotExist, ValueError):
            return JsonResponse({'error': 'Datos inválidos'}, status=400)


    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            if not hasattr(request.user, 'customer'):
                messages.error(request, "Tu cuenta no está registrada como cliente.")
                return redirect('home')

            customer = request.user.customer
            try:
                create_appointment(form, business, customer=customer)  # usamos la función centralizada
                messages.success(request, "Cita agendada exitosamente.")
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
        form.fields['barber'].queryset = employees

    return render(request, 'book_appointment.html', {
        'form': form,
        'business': business,
        'services': services,
        'employees': employees,
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