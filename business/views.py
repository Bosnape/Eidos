import uuid
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
from .models import BusinessAccount, RegistrationSession, Account, Service, Employee, PortfolioItem, Appointment
from .forms import BusinessInfoForm, BusinessUserForm, LoginForm, BusinessProfileForm, ServiceForm, SocialMediaForm, EmployeeForm, PortfolioItemForm

from datetime import datetime, timedelta
from django.db.models import Sum, Avg

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

