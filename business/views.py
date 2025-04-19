import uuid
import os
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Q, Sum, Avg
from django.utils import timezone

from .models import (
    BusinessAccount, RegistrationSession, Account, Service, 
    Employee, PortfolioItem, Appointment, Schedule, Shift, 
    Availability, StaffAppointment
)
from .forms import (
    BusinessInfoForm, BusinessUserForm, LoginForm, BusinessProfileForm, 
    ServiceForm, SocialMediaForm, EmployeeForm, PortfolioItemForm,
    ScheduleForm, ShiftFormSet, AvailabilityForm, StaffAppointmentForm
)

from .appointment_charts import generateAllCharts


def registerBusinessInfo(request):
    if request.user.is_authenticated:
        return redirect('business_dashboard')
    
    if request.method == 'POST':
        form = BusinessInfoForm(request.POST, request.FILES)
        if form.is_valid():
            # Create a unique session key
            session_key = str(uuid.uuid4())
            
            # Create registration session but don't save the instance yet
            reg_session = form.save(commit=False)
            reg_session.session_key = session_key
            reg_session.save()
            
            # Store session key in the user's session
            request.session['registration_session_key'] = session_key
            
            # Redirect to phase 2
            return redirect('register_UBusiness')
    else:
        form = BusinessInfoForm()
    
    return render(request, 'register_information.html', {'form': form})

def registerBusinessUser(request):
    if request.user.is_authenticated:
        return redirect('business_dashboard')
    
    # Check if user has completed phase 1
    session_key = request.session.get('registration_session_key')
    if not session_key:
        messages.error(request, "Please complete the first phase of registration")
        return redirect('register_IBusiness')
    
    try:
        reg_session = RegistrationSession.objects.get(session_key=session_key)
    except RegistrationSession.DoesNotExist:
        messages.error(request, "Registration session expired. Please start again.")
        return redirect('register_IBusiness')
    
    if request.method == 'POST':
        form = BusinessUserForm(request.POST)
        if form.is_valid():
            # Create user account
            user = Account.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1']
            )
            
            # Create business account
            business = BusinessAccount(
                name=reg_session.name,
                email=reg_session.email,
                address=reg_session.address,
                phone=reg_session.phone,
                user=user
            )
            
            # Handle logo upload
            if reg_session.logo:
                business.logo = reg_session.logo
                # Note: In production, you would want to move the file from 
                # temp directory to the final directory
            
            business.save()
            
            # Clean up the session data
            del request.session['registration_session_key']
            reg_session.delete()
            
            # Log the user in
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('business_dashboard')
    else:
        form = BusinessUserForm()
    
    return render(request, 'register_credentials.html', {'form': form})

def loginBusiness(request):
    if request.user.is_authenticated:
        return redirect('business_dashboard')
        
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, "Welcome back!")
                
                # Redirect to the page the user was trying to access, or dashboard
                next_page = request.GET.get('next', 'business_dashboard')
                return redirect(next_page)
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

@login_required
def logoutBusiness(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('home')

def displayProfile(request, business_name):
    try:
        # Get the specific business by name (case-insensitive)
        business = BusinessAccount.objects.filter(name__iexact=business_name).first()
        if business is None:
            messages.error(request, f"Business '{business_name}' not found.")
            return redirect('home')
        
        services = Service.objects.filter(business=business)
        return render(request, "public_profile.html", {'business': business, 'services': services})
    except Exception as e:
        messages.error(request, f"Error finding business: {str(e)}")
        return redirect('home')

@login_required
def provideDashboardSection(request):
    """Main dashboard view that displays business statistics and charts"""
    
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    # Get statistics data with time-based summaries
    stats_data = getDashboardStatisticsSummary(business)
    
    # Generate all charts using the utility function
    charts = generateAllCharts(business)
    
    portfolio_items = business.portfolio_items.all()
    context = {
        'business': business,
        'portfolio_items': portfolio_items,
        'stats_data': stats_data,
        'charts': charts,
    }    
    return render(request, 'dashboard.html', context)

def getDashboardStatisticsSummary(business):
    """Prepare all statistics data summaries for the dashboard"""
    
    today = datetime.today()
    
    start_of_month = today.replace(day=1)
    # Limit end_of_month to today if today is before the actual end of month
    end_of_month_full = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    end_of_month = min(today, end_of_month_full)
    start_of_year = today.replace(month=1, day=1)
    
    # Get all appointments for this business
    appointments = Appointment.objects.filter(business=business)
    
    # Daily statistics
    today_appointments = appointments.filter(date=today)
    daily_appointments_count = today_appointments.count()
    daily_new_clients = today_appointments.filter(repeat_customer=False).count()
    daily_avg_rating = today_appointments.filter(customer_satisfaction__gt=0).aggregate(avg=Avg('customer_satisfaction'))['avg'] or 0
    daily_revenue = today_appointments.aggregate(sum=Sum('price'))['sum'] or 0
    
    # Monthly statistics
    month_appointments = appointments.filter(date__gte=start_of_month, date__lte=end_of_month)
    monthly_appointments_count = month_appointments.count()
    monthly_new_clients = month_appointments.filter(repeat_customer=False).count()
    monthly_avg_rating = month_appointments.filter(customer_satisfaction__gt=0).aggregate(avg=Avg('customer_satisfaction'))['avg'] or 0
    monthly_revenue = month_appointments.aggregate(sum=Sum('price'))['sum'] or 0
    
    # Annual statistics
    year_appointments = appointments.filter(date__gte=start_of_year, date__lte=today)
    annual_appointments_count = year_appointments.count()
    annual_total_clients = year_appointments.values('customer_email').distinct().count()
    annual_avg_rating = year_appointments.filter(customer_satisfaction__gt=0).aggregate(avg=Avg('customer_satisfaction'))['avg'] or 0
    annual_revenue = year_appointments.aggregate(sum=Sum('price'))['sum'] or 0
    
    # Basic stats for the top cards
    todays_appointments = appointments.filter(date=today).count()
    total_clients = appointments.values('customer_email').distinct().count()
    avg_rating = appointments.filter(customer_satisfaction__gt=0).aggregate(avg=Avg('customer_satisfaction'))['avg'] or 0
    monthly_revenue_basic = appointments.filter(date__gte=start_of_month, date__lte=end_of_month).aggregate(sum=Sum('price'))['sum'] or 0
    
    # Return the time-based summaries
    return {
        'daily_stats': {
            'appointments': daily_appointments_count,
            'new_clients': daily_new_clients,
            'avg_rating': round(daily_avg_rating, 1),
            'revenue': round(daily_revenue, 2),
        },
        'monthly_stats': {
            'appointments': monthly_appointments_count,
            'new_clients': monthly_new_clients,
            'avg_rating': round(monthly_avg_rating, 1),
            'revenue': round(monthly_revenue, 2),
        },
        'annual_stats': {
            'appointments': annual_appointments_count,
            'total_clients': annual_total_clients,
            'avg_rating': round(annual_avg_rating, 1),
            'revenue': round(annual_revenue, 2),
        },
        'basic_stats': {
            'todays_appointments': todays_appointments,
            'total_clients': total_clients,
            'avg_rating': round(avg_rating, 1),
            'monthly_revenue': monthly_revenue_basic,
        },
    }

@login_required
def manageProfile(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('business_dashboard')
        
    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, request.FILES, instance=business)
        if 'logo' in request.FILES:
            if business.logo and business.logo.name:
                try:
                    old_logo_path = business.logo.path
                    if os.path.isfile(old_logo_path):
                        os.remove(old_logo_path)
                except Exception as e:
                    print(f"Error deleting old logo: {str(e)}")
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('business_dashboard')
    else:
        form = BusinessProfileForm(instance=business)
        
    return render(request, 'manage.html', {'form': form, 'business': business})

@login_required
def updateSocialMedia(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')

    if request.method == "POST":
        form = SocialMediaForm(request.POST, instance=business)
        if form.is_valid():
            form.save()
            return redirect('business_dashboard') 

    else:
        form = SocialMediaForm(instance=business)

    return render(request, 'update_social_media.html', {'form': form, 'business': business})

@login_required
def dashboardServicesView(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    services = Service.objects.filter(business=business)
    return render(request, 'dashboard_services.html', {'business': business, 'services': services})

@login_required
def addService(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')

    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save(commit=False)
            service.business = business  # Asigna el negocio al servicio
            service.save()
            messages.success(request, "Service added successfully!")
            return redirect('dashboard_services')

    else:
        form = ServiceForm()

    all_services = Service.objects.filter(business=business)
    return render(request, 'service_form.html', {'form': form, 'business': business, 'all_services': all_services})

@login_required
def editService(request, service_id):
    try:
        service = Service.objects.filter(id=service_id).first()
    except Service.DoesNotExist:
        messages.error(request, "Service not found")
        return redirect('home')

    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated successfully!")
            return redirect('dashboard_services') 
    else:
        form = ServiceForm(instance=service)
        
    all_services = Service.objects.filter(business=service.business)
    return render(request, 'service_form.html', {'form': form, 'service': service, 'business': service.business, 'all_services': all_services})

@login_required
def deleteService(request, service_id):
    try:
        service = Service.objects.filter(id=service_id).first()
    except Service.DoesNotExist:
        messages.error(request, "Service not found")
        return redirect('home')

    service.delete()
    messages.success(request, "Service deleted successfully!")
    return redirect('dashboard_services')

@login_required
def listEmployee(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    employees = Employee.objects.filter(business=business)
    return render(request, 'employee_list.html', {'business': business, 'employees': employees})

@login_required
def addEmployee(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.business = business
            employee.save()
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'add_employee.html', {'form': form, 'business': business})

@login_required
def listPortfolio(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    portfolio_items = PortfolioItem.objects.filter(business=business)
    return render(request, 'portfolio_list.html', {'business': business, 'portfolio_items': portfolio_items})

@login_required
def addPortfolio(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    if request.method == 'POST':
        form = PortfolioItemForm(request.POST, request.FILES)
        if form.is_valid():
            portfolio_item = form.save(commit=False)
            portfolio_item.business = business
            portfolio_item.save()
            return redirect('portfolio_list')
    else:
        form = PortfolioItemForm()
    
    return render(request, 'add_portfolio.html', {'business': business, 'form': form})

@login_required
def create_schedule(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    if request.method == 'POST':
        schedule_form = ScheduleForm(request.POST)
        shift_formset = ShiftFormSet(request.POST, prefix='shifts')
        
        if schedule_form.is_valid() and shift_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save schedule
                    schedule = schedule_form.save(commit=False)
                    # Verify employee belongs to this business
                    if schedule.employee.business != business:
                        messages.error(request, "Invalid employee selected")
                        raise Exception("Invalid employee")
                    schedule.save()
                    
                    # Save shifts
                    shifts = shift_formset.save(commit=False)
                    for shift in shifts:
                        shift.schedule = schedule
                        shift.save()
                    
                    # Handle deleted shifts
                    for obj in shift_formset.deleted_objects:
                        obj.delete()
                    
                    messages.success(request, f"Schedule for {schedule.employee.name} created successfully!")
                    return redirect('schedule_list')
            except Exception as e:
                messages.error(request, f"Error creating schedule: {str(e)}")
    else:
        schedule_form = ScheduleForm()
        # Filter employees to only show those from this business
        schedule_form.fields['employee'].queryset = Employee.objects.filter(business=business)
        shift_formset = ShiftFormSet(prefix='shifts')
    
    return render(request, 'schedule_form.html', {
        'schedule_form': schedule_form,
        'shift_formset': shift_formset,
        'business': business,
        'is_edit': False
    })

# FR05.2 - Staff shift editing and updating
@login_required
def edit_schedule(request, schedule_id):
    try:
        business = BusinessAccount.objects.get(user=request.user)
        schedule = get_object_or_404(Schedule, id=schedule_id)
        
        # Verify the schedule belongs to an employee of this business
        if schedule.employee.business != business:
            messages.error(request, "You don't have permission to edit this schedule")
            return redirect('schedule_list')
            
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    if request.method == 'POST':
        schedule_form = ScheduleForm(request.POST, instance=schedule)
        shift_formset = ShiftFormSet(request.POST, prefix='shifts', queryset=Shift.objects.filter(schedule=schedule))
        
        if schedule_form.is_valid() and shift_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save schedule
                    updated_schedule = schedule_form.save()
                    
                    # Save shifts
                    shifts = shift_formset.save(commit=False)
                    for shift in shifts:
                        shift.schedule = updated_schedule
                        shift.save()
                    
                    # Handle deleted shifts
                    for obj in shift_formset.deleted_objects:
                        obj.delete()
                    
                    messages.success(request, f"Schedule for {updated_schedule.employee.name} updated successfully!")
                    return redirect('schedule_list')
            except Exception as e:
                messages.error(request, f"Error updating schedule: {str(e)}")
    else:
        schedule_form = ScheduleForm(instance=schedule)
        # Filter employees to only show those from this business
        schedule_form.fields['employee'].queryset = Employee.objects.filter(business=business)
        shift_formset = ShiftFormSet(prefix='shifts', queryset=Shift.objects.filter(schedule=schedule))
    
    return render(request, 'schedule_form.html', {
        'schedule_form': schedule_form,
        'shift_formset': shift_formset,
        'business': business,
        'schedule': schedule,
        'is_edit': True
    })

# FR05.3 - Staff schedule deletion
@login_required
def delete_schedule(request, schedule_id):
    try:
        business = BusinessAccount.objects.get(user=request.user)
        schedule = get_object_or_404(Schedule, id=schedule_id)
        
        # Verify the schedule belongs to an employee of this business
        if schedule.employee.business != business:
            messages.error(request, "You don't have permission to delete this schedule")
            return redirect('schedule_list')
            
        employee_name = schedule.employee.name
        schedule.delete()
        messages.success(request, f"Schedule for {employee_name} deleted successfully!")
        
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
    except Exception as e:
        messages.error(request, f"Error deleting schedule: {str(e)}")
    
    return redirect('schedule_list')

# FR05.4 - Staff schedule viewing functionality
@login_required
def schedule_list(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    # Get all employees for this business
    employees = Employee.objects.filter(business=business)
    
    # Get all schedules for these employees
    schedules = Schedule.objects.filter(employee__in=employees).order_by('-is_active', 'employee__name')
    
    return render(request, 'schedule_list.html', {
        'business': business,
        'schedules': schedules
    })

# FR05.6 - Staff availability registration
@login_required
def manage_availability(request, employee_id=None):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    # If employee_id is provided, get that specific employee
    if employee_id:
        employee = get_object_or_404(Employee, id=employee_id, business=business)
        employees = [employee]
    else:
        # Otherwise, get all employees for this business
        employees = Employee.objects.filter(business=business)
        if not employees:
            messages.warning(request, "You need to add employees before managing availability")
            return redirect('employee_list')
        employee = employees.first()
    
    # Get date range for calendar (current month)
    today = timezone.now().date()
    start_date = today.replace(day=1)
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
    
    # Get all availabilities for this employee in the date range
    availabilities = Availability.objects.filter(
        employee=employee,
        date__range=[start_date, end_date]
    )
    
    # Create a calendar data structure
    calendar_data = []
    current_date = start_date
    while current_date <= end_date:
        # Find availability for this date if it exists
        availability = availabilities.filter(date=current_date).first()
        
        # Get the employee's schedule for this day of the week
        day_of_week = current_date.weekday()
        shifts = Shift.objects.filter(
            schedule__employee=employee,
            schedule__is_active=True,
            schedule__start_date__lte=current_date,
            day_of_week=day_of_week
        ).filter(
            models.Q(schedule__end_date__isnull=True) | 
            models.Q(schedule__end_date__gte=current_date)
        )
        
        # Add this date to the calendar
        calendar_data.append({
            'date': current_date,
            'day_name': current_date.strftime('%a'),
            'is_today': current_date == today,
            'availability': availability,
            'shifts': shifts
        })
        
        current_date += timedelta(days=1)
    
    # Handle form submission for updating availability
    if request.method == 'POST':
        date_str = request.POST.get('date')
        is_available = request.POST.get('is_available') == 'true'
        reason = request.POST.get('reason', '')
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Update or create availability record
            availability, created = Availability.objects.update_or_create(
                employee=employee,
                date=date,
                defaults={'is_available': is_available, 'reason': reason}
            )
            
            messages.success(request, f"Availability for {employee.name} on {date} updated successfully!")
            return redirect('manage_availability', employee_id=employee.id)
            
        except Exception as e:
            messages.error(request, f"Error updating availability: {str(e)}")
    
    return render(request, 'manage_availability.html', {
        'business': business,
        'employee': employee,
        'employees': employees,
        'calendar_data': calendar_data,
        'month_name': start_date.strftime('%B %Y')
    })

# View for calendar display of all staff schedules
@login_required
def staff_calendar(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    # Get all employees for this business
    employees = Employee.objects.filter(business=business)
    
    # Get date range for calendar (current week by default)
    today = timezone.now().date()
    
    # Get the requested date from query parameters, or use today
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today
    
    # Calculate the start of the week (Monday)
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Prepare calendar data
    calendar_data = {
        'days': [],
        'employees': []
    }
    
    # Add days to calendar
    current_date = start_of_week
    while current_date <= end_of_week:
        calendar_data['days'].append({
            'date': current_date,
            'day_name': current_date.strftime('%a'),
            'is_today': current_date == today
        })
        current_date += timedelta(days=1)
    
    # Add employees and their schedules to calendar
    for employee in employees:
        employee_data = {
            'employee': employee,
            'days': []
        }
        
        # For each day in the week
        current_date = start_of_week
        while current_date <= end_of_week:
            # Get availability for this date
            availability = Availability.objects.filter(
                employee=employee,
                date=current_date
            ).first()
            
            # Get shifts for this day of the week
            day_of_week = current_date.weekday()
            shifts = Shift.objects.filter(
                schedule__employee=employee,
                schedule__is_active=True,
                schedule__start_date__lte=current_date,
                day_of_week=day_of_week
            ).filter(
                models.Q(schedule__end_date__isnull=True) | 
                models.Q(schedule__end_date__gte=current_date)
            )
            
            # Get appointments for this date
            appointments = Appointment.objects.filter(
                employee=employee,
                date=current_date
            ).order_by('start_time')
            
            employee_data['days'].append({
                'date': current_date,
                'availability': availability,
                'shifts': shifts,
                'appointments': appointments,
                'is_available': availability.is_available if availability else True
            })
            
            current_date += timedelta(days=1)
        
        calendar_data['employees'].append(employee_data)
    
    # Calculate previous and next week dates for navigation
    prev_week = start_of_week - timedelta(days=7)
    next_week = start_of_week + timedelta(days=7)
    
    return render(request, 'staff_calendar.html', {
        'business': business,
        'calendar_data': calendar_data,
        'week_start': start_of_week,
        'week_end': end_of_week,
        'prev_week': prev_week,
        'next_week': next_week
    })

# View for managing appointments
@login_required
def manage_appointments(request):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    # Get all appointments for this business
    appointments = Appointment.objects.filter(business=business).order_by('date', 'start_time')
    
    # Filter appointments by status if requested
    status_filter = request.GET.get('status')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    # Filter appointments by date range if requested
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            appointments = appointments.filter(date__gte=start_date)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            appointments = appointments.filter(date__lte=end_date)
        except ValueError:
            pass
    
    return render(request, 'manage_appointments.html', {
        'business': business,
        'appointments': appointments,
        'status_filter': status_filter,
        'start_date': start_date_str,
        'end_date': end_date_str
    })

# View for creating a new appointment
@login_required
def create_staff_appointment(request):
    """Vista para crear una nueva cita de personal"""
    business = request.user.businessaccount  # Ajusta según tu configuración
    
    # Prellenar con empleado y fecha si se proporcionan en la URL
    initial_data = {}
    if request.GET.get('employee'):
        initial_data['employee'] = request.GET.get('employee')
    if request.GET.get('date'):
        initial_data['date'] = request.GET.get('date')
    
    if request.method == 'POST':
        form = StaffAppointmentForm(request.POST, initial=initial_data)
        
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.business = business
            appointment.save()
            return redirect('manage_staff_appointments')
    else:
        form = StaffAppointmentForm(initial=initial_data)
        # Filtrar empleados y servicios por negocio
        form.fields['employee'].queryset = Employee.objects.filter(business=business)
        form.fields['service'].queryset = Service.objects.filter(business=business)
    
    return render(request, 'staff_appointment_form.html', {
        'form': form,
        'is_edit': False,
        'business': business,
    })

@login_required
def manage_staff_appointments(request):
    """
    Vista para gestionar las citas del personal.
    Muestra una lista de todas las citas del personal asociadas al negocio.
    """
    business = get_object_or_404(BusinessAccount, user=request.user)
    appointments = StaffAppointment.objects.filter(business=business).order_by('-date', '-start_time')
    
    context = {
        'business': business,
        'appointments': appointments,
    }
    
    return render(request, 'staff_appointments.html', context)

@login_required
def edit_staff_appointment(request, appointment_id):
    """
    Vista para editar una cita de personal existente.
    """
    business = get_object_or_404(BusinessAccount, user=request.user)
    appointment = get_object_or_404(StaffAppointment, id=appointment_id, business=business)
    
    if request.method == 'POST':
        form = StaffAppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cita actualizada exitosamente.')
            return redirect('manage_staff_appointments')
    else:
        form = StaffAppointmentForm(instance=appointment)
        # Filtrar empleados por negocio
        form.fields['employee'].queryset = Employee.objects.filter(business=business)
    
    context = {
        'business': business,
        'form': form,
        'appointment': appointment,
        'action': 'edit'
    }
    
    return render(request, 'staff_appointment_form.html', context)

@login_required
def delete_staff_appointment(request, appointment_id):
    """
    Vista para eliminar una cita de personal.
    """
    business = get_object_or_404(BusinessAccount, user=request.user)
    appointment = get_object_or_404(StaffAppointment, id=appointment_id, business=business)
    
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, 'Cita eliminada exitosamente.')
        return redirect('manage_staff_appointments')
    
    context = {
        'business': business,
        'appointment': appointment
    }
    
    return render(request, 'confirm_delete_staff_appointment.html', context)