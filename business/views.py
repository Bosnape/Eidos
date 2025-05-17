import uuid
import os
import re
from django.http import JsonResponse
from django.contrib.auth import login, get_user_model
from datetime import datetime, timedelta, date
from pydantic import ValidationError
from django.views.decorators.http import require_GET

from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models, transaction
from django.db.models import Sum, Avg
from django.utils import timezone
from .appointment_charts import *
from django import forms

from .models import (
    BusinessAccount, RegistrationSession, Account, Service, 
    Employee, PortfolioItem, Appointment, Schedule, Shift, 
    Availability
)
from .forms import (
    BusinessInfoForm, BusinessUserForm, BusinessProfileForm, 
    ServiceForm, SocialMediaForm, EmployeeForm, PortfolioItemForm,
    ScheduleForm, ShiftFormSet, AppointmentForm
)

from openai import OpenAI
from dotenv import load_dotenv
from .utils import create_appointment  

Account = get_user_model()

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
            
            # Marcar la cuenta como negocio
            user.is_business = True
            user.save()
            
            # Create business account
            business = BusinessAccount(
                name=reg_session.name,
                email=reg_session.email,
                address=reg_session.address,
                phone=reg_session.phone,
                user=user
            )
            
            if reg_session.logo:
                business.logo = reg_session.logo
            
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
    stats_data = getStatisticsSummary(business)
    
    # Generate all charts for the dashboard
    charts = generateAllCharts(business)
    
     # Initialize summaries as None
    monthly_summary = None
    annual_summary = None
    
    # Check if summary was requested (button clicked)
    if request.GET.get('generate_summary') == 'true':
        time_frame = request.GET.get('time_frame', 'monthly')
        try:
            if time_frame == 'annual':
                annual_summary = getAnnualSummary(business)
                # Clear any existing monthly summary
                monthly_summary = None
            else:
                monthly_summary = getMonthlySummary(business)
                # Clear any existing annual summary
                annual_summary = None
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'summary': annual_summary if time_frame == 'annual' else monthly_summary,
                    'time_frame': time_frame,
                    'status': 'success'
                })
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
            messages.error(request, f"Error generating insights: {str(e)}")
     
    portfolio_items = business.portfolio_items.all()
    context = {
        'business': business,
        'portfolio_items': portfolio_items,
        'stats_data': stats_data,
        'charts': charts,
        'monthly_summary': monthly_summary,
        'annual_summary': annual_summary,
    }    
     
    return render(request, 'dashboard.html', context)

def getStatisticsSummary(business):
    """Prepare all statistics data summaries for the dashboard"""
    
    today = datetime.today()
    
    start_of_month = today.replace(day=1)
    
    # Limit end_of_month to today if today is before the actual end of month
    end_of_month_full = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    end_of_month = min(today, end_of_month_full)
    start_of_year = today.replace(month=1, day=1)
    
    # Get all appointments for this business
    appointments = Appointment.objects.filter(business=business, status__in=['scheduled', 'completed'])
    
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
    }

def generateAllCharts(business):
    """Generate all charts for the dashboard"""
    
    charts = {
        # Daily charts
        'time_slot_chart': generateTimeSlotChart(business),
        'customer_type_day_chart': generateCustomerTypesChart(business, 'day'),
        
        # Monthly charts
        'revenue_by_day_chart': generateRevenueChart(business, 'month'),
        'appointments_by_day_chart': generateAppointmentsByDayChart(business),
        'top_services_month_chart': generateTopServicesChart(business, 'month'),
        'barber_performance_chart': generateBarberPerformanceChart(business, 'month'),
        'satisfaction_by_day_chart': generateSatisfactionChart(business, 'month'),
        'no_show_rate_chart': generateNoShowChart(business, 'month'),
        'customer_type_month_chart': generateCustomerTypesChart(business, 'month'),
        
        # Annual charts
        'monthly_revenue_chart': generateRevenueChart(business, 'year'),
        'top_services_year_chart': generateTopServicesChart(business, 'year'),
        'barber_leaderboard_chart': generateBarberPerformanceChart(business, 'year'),
        'no_show_rate_year_chart': generateNoShowChart(business, 'year'),
        'monthly_rating_chart': generateSatisfactionChart(business, 'year'),
        'customer_type_year_chart': generateCustomerTypesChart(business, 'year'),
    }
    
    return charts

def getMonthlySummary(business):
    """Get monthly summary of appointments for the business using openAI"""
    
    appointments = Appointment.objects.filter(business=business, status__in=['scheduled', 'completed'])
    
    # Get this month's data
    today = datetime.today()
    
    start_of_month = today.replace(day=1)
    end_of_month_full = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    end_of_month = min(today, end_of_month_full)
    
    this_month_appointments = appointments.filter(date__gte=start_of_month, date__lte=end_of_month)
    this_month_appointments_count = this_month_appointments.count()
    
    this_month_new_clients = this_month_appointments.filter(repeat_customer=False).count()
    this_month_repeat_clients = this_month_appointments.filter(repeat_customer=True).count()
    if this_month_new_clients > 0:
        this_month_repeat_new_ratio = f"{this_month_repeat_clients}:{this_month_new_clients}"
    else:
        this_month_repeat_new_ratio = "N/A"
    
    this_month_avg_rating = this_month_appointments.filter(customer_satisfaction__gt=0).aggregate(avg=Avg('customer_satisfaction'))['avg'] or 0
    this_month_revenue = this_month_appointments.aggregate(sum=Sum('price'))['sum'] or 0
    this_month_no_shows = this_month_appointments.filter(no_show=True).count()
    this_month_no_show_rate = round((this_month_no_shows / this_month_appointments_count * 100) if this_month_appointments_count > 0 else 0, 1)
    
    # Get last month's data
    last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
    last_month_end = start_of_month - timedelta(days=1)  
    
    last_month_appointments = appointments.filter(date__gte=last_month_start, date__lte=last_month_end)
    last_month_appointments_count = last_month_appointments.count()
    
    last_month_new_clients = last_month_appointments.filter(repeat_customer=False).count()
    last_month_repeat_clients = last_month_appointments.filter(repeat_customer=True).count()
    if last_month_new_clients > 0:
        last_month_repeat_new_ratio = f"{last_month_repeat_clients}:{last_month_new_clients}"
    else:
        last_month_repeat_new_ratio = "N/A"
        
    last_month_avg_rating = last_month_appointments.filter(customer_satisfaction__gt=0).aggregate(avg=Avg('customer_satisfaction'))['avg'] or 0
    last_month_revenue = last_month_appointments.aggregate(sum=Sum('price'))['sum'] or 0
    last_month_no_shows = last_month_appointments.filter(no_show=True).count()
    last_month_no_show_rate = round((last_month_no_shows / last_month_appointments_count * 100) if last_month_appointments_count > 0 else 0, 1)
    
    load_dotenv('api_keys.env')
    client = OpenAI(api_key=os.environ.get('openai_apikey'))
    
    instruction = (
        "Compare this month's performance with last month's using these metrics: "
        "Appointments, New Clients, Repeat Clients, Repeat/New Ratio, Rating, No Shows, "
        "No Show Rate, and Revenue. First, describe how the metrics changed (avoid the use of 'versus'). "
        "Then, provide a concise summary in bullet points highlighting key changes, improvements, or issues. "
        "Keep it clear, useful, and business-owner friendly. Start each section with the titles: "
        "'Performance Overview:' and 'Key Insights:' exactly as written, and do not provide any other title/section. Here is the data:\n"
    )
    
    data = (
        "\nThis month: \n"
        f"Appointments: {this_month_appointments_count}\n"
        f"New Clients: {this_month_new_clients}\n"
        f"Repeat Clients: {this_month_repeat_clients}\n"
        f"Repeat/New Ratio: {this_month_repeat_new_ratio}\n"
        f"Rating: {this_month_avg_rating}\n"
        f"No Shows: {this_month_no_shows}\n"
        f"No Show Rate: {this_month_no_show_rate}%\n"
        f"Revenue: {this_month_revenue}\n"
        
        "\nLast month:\n"
        f"Appointments: {last_month_appointments_count}\n"
        f"New Clients: {last_month_new_clients}\n"
        f"Repeat Clients: {last_month_repeat_clients}\n"
        f"Repeat/New Ratio: {last_month_repeat_new_ratio}\n"
        f"Rating: {last_month_avg_rating}\n"
        f"No Shows: {last_month_no_shows}\n"
        f"No Show Rate: {last_month_no_show_rate}%\n"
        f"Revenue: {last_month_revenue}\n"
    )
    
    prompt = (
        f"{instruction}"
        f"{data}"
    )
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0,
    )
    content  = response.choices[0].message.content.strip()
    
    # Parse the response into sections using regex
    sections = []
    pattern = r'(Performance Overview:|Key Insights:)(.*?)(?=(Performance Overview:|Key Insights:|$))'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        title = match[0].replace(':', '').strip()
        items_text = match[1].strip()
        
        # Extract bullet points or split lines
        items = []
        if '-' in items_text:
            # Handle bullet points
            items = [item.strip() for item in items_text.split('-') if item.strip()]
        else:
            # Handle line breaks
            items = [item.strip() for item in items_text.split('\n') if item.strip()]
        
        sections.append({
            'title': title,
            'items': items
        })
        print(f"Title: {title}, Items: {items}")
    
    # Fallback if parsing fails
    if not sections:
        sections = [{
            'title': 'Monthly Analysis',
            'items': [content]
        }]
    
    return sections

def getAnnualSummary(business):
    """Get month-by-month annual summary of appointments for the business using openAI"""
    
    appointments = Appointment.objects.filter(business=business, status__in=['scheduled', 'completed'])
    today = datetime.today()
    current_year = today.year
    
    # Prepare month-by-month data
    monthly_data = []
    for month in range(1, today.month + 1):
        month_start = datetime(current_year, month, 1).date()
        if month < 12:
            month_end = datetime(current_year, month + 1, 1).date() - timedelta(days=1)
        else:
            month_end = datetime(current_year, 12, 31).date()
        
        # Limit end date to today for current month
        if month == today.month:
            month_end = min(today.date(), month_end)
        
        month_appointments = appointments.filter(date__gte=month_start, date__lte=month_end)
        month_count = month_appointments.count()
        
        monthly_data.append({
            'month': month_start.strftime("%B"),
            'appointments': month_count,
            'new_clients': month_appointments.filter(repeat_customer=False).count(),
            'repeat_clients': month_appointments.filter(repeat_customer=True).count(),
            'avg_rating': month_appointments.filter(customer_satisfaction__gt=0).aggregate(avg=Avg('customer_satisfaction'))['avg'] or 0,
            'revenue': month_appointments.aggregate(sum=Sum('price'))['sum'] or 0,
            'no_shows': month_appointments.filter(no_show=True).count(),
            'no_show_rate': round((month_appointments.filter(no_show=True).count() / month_count * 100) if month_count > 0 else 0, 1)
        })
    
    # Calculate year-to-date totals
    ytd_appointments = sum(m['appointments'] for m in monthly_data)
    ytd_new_clients = sum(m['new_clients'] for m in monthly_data)
    ytd_repeat_clients = sum(m['repeat_clients'] for m in monthly_data)
    ytd_revenue = sum(m['revenue'] for m in monthly_data)
    ytd_no_shows = sum(m['no_shows'] for m in monthly_data)
    
    # Calculate averages
    months_with_ratings = [m for m in monthly_data if m['avg_rating'] > 0]
    ytd_avg_rating = round(sum(m['avg_rating'] for m in months_with_ratings) / len(months_with_ratings), 1) if months_with_ratings else 0
    ytd_no_show_rate = round((ytd_no_shows / ytd_appointments * 100) if ytd_appointments > 0 else 0, 1)
    
    load_dotenv('api_keys.env')
    client = OpenAI(api_key=os.environ.get('openai_apikey'))
    
    instruction = (
        "Provide a month-by-month overview of business performance for the current year up to today. "
        "Analyze trends in these metrics: Appointments, New Clients, Repeat Clients, Rating, Revenue, and No-show Rate. "
        "Highlight any significant monthly patterns or anomalies. For each month, create a subtitle with the month name followed by a colon. "
        "Then, summarize the year-to-date performance and key takeaways. "
        "Keep the analysis concise and actionable for a business owner. "
        "Start each section with these exact titles: "
        "'Month-by-Month Analysis:' and 'Year-to-Date Summary:', and do not provide any other title/section. Here is the data:\n\n"
        f"Current Year: {current_year} (Data through {today.strftime('%B %d')})\n\n"
        "Monthly Data:\n"
    )
    
    # Add monthly data to prompt
    monthly_data_text = ""
    for month in monthly_data:
        monthly_data_text += (
            f"{month['month']}:\n"
            f"  Appointments: {month['appointments']}\n"
            f"  New Clients: {month['new_clients']}\n"
            f"  Repeat Clients: {month['repeat_clients']}\n"
            f"  Avg Rating: {month['avg_rating']}\n"
            f"  Revenue: ${month['revenue']:.2f}\n"
            f"  No-show Rate: {month['no_show_rate']}%\n\n"
        )
    
    # Add YTD summary to prompt
    ytd_text = (
        "\nYear-to-Date Totals:\n"
        f"Total Appointments: {ytd_appointments}\n"
        f"New Clients: {ytd_new_clients}\n"
        f"Repeat Clients: {ytd_repeat_clients}\n"
        f"Avg Rating: {ytd_avg_rating}\n"
        f"Total Revenue: ${ytd_revenue:.2f}\n"
        f"No-show Rate: {ytd_no_show_rate}%\n"
    )
    
    prompt = (
        f"{instruction}"
        f"{monthly_data_text}"
        f"{ytd_text}"
    )
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,  # Increased for more detailed analysis
        temperature=0,
    )
    content = response.choices[0].message.content.strip()
    
    # Parse the response into sections
    sections = []
    current_section = None
    current_subsection = None
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Check for section title
        if line.endswith('Analysis:') or line.endswith('Summary:'):
            if current_section:
                if current_subsection:
                    current_section['subsections'].append(current_subsection)
                sections.append(current_section)
            current_section = {
                'title': line.replace(':', ''),
                'subsections': []
            }
            current_subsection = None
            
        # Check for subtitle (month name)
        elif line.endswith(':'):
            if current_subsection and current_section:
                current_section['subsections'].append(current_subsection)
            current_subsection = {
                'title': line.replace(':', '').strip(),
                'items': []
            }
            
        # Check for bullet points
        elif line.startswith('-'):
            if current_subsection:
                current_subsection['items'].append(line[1:].strip())
            elif current_section:
                # Handle items that belong to the section directly (like in Year-to-Date Summary)
                if 'items' not in current_section:
                    current_section['items'] = []
                current_section['items'].append(line[1:].strip())
    
    # Add any remaining sections/subsections
    if current_subsection and current_section:
        current_section['subsections'].append(current_subsection)
    if current_section:
        sections.append(current_section)
    
    return sections

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
def listEmployees(request):
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
def createSchedule(request):
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
def editSchedule(request, schedule_id):
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
def deleteSchedule(request, schedule_id):
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
def listSchedules(request):
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

@login_required
def manageAvailability(request, employee_id=None):
    try:
        business = BusinessAccount.objects.get(user=request.user)
    except BusinessAccount.DoesNotExist:
        messages.error(request, "Business profile not found")
        return redirect('home')
    
    # Manejo de redirección si no hay empleados
    employees = Employee.objects.filter(business=business)
    if not employees.exists():
        messages.warning(request, "You need to add employees before managing availability")
        return redirect('employee_list')
    
    # Si se proporciona employee_id, obtener ese empleado específico
    if employee_id:
        try:
            employee = Employee.objects.get(id=employee_id, business=business)
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found")
            return redirect('manage_availability')
    else:
        employee = employees.first()
    
    # Get year and month from query parameters
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    today = timezone.now().date()
    
    # Set start_date based on year and month parameters if provided
    if year and month:
        try:
            year = int(year)
            month = int(month)
            start_date = date(year, month, 1)
        except (ValueError, TypeError):
            # Fall back to current month if invalid parameters
            start_date = today.replace(day=1)
    else:
        # Use current month if no parameters
        start_date = today.replace(day=1)
    
    # Calcular fecha final del mes
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
    
    # Obtener todas las disponibilidades para este empleado en el rango de fechas
    availabilities = Availability.objects.filter(
        employee=employee,
        date__range=[start_date, end_date]
    )
    
    # Crear estructura de datos para el calendario
    calendar_data = []
    current_date = start_date
    while current_date <= end_date:
        # Buscar disponibilidad para esta fecha si existe
        availability = availabilities.filter(date=current_date).first()
        
        # Obtener el horario del empleado para este día de la semana
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
        
        # Agregar esta fecha al calendario
        calendar_data.append({
            'date': current_date,
            'day_name': current_date.strftime('%a'),
            'is_today': current_date == today,
            'availability': availability,
            'shifts': shifts
        })
        
        current_date += timedelta(days=1)
    
    # Manejar envío del formulario para actualizar disponibilidad
    if request.method == 'POST':
        date_str = request.POST.get('date')
        is_available = request.POST.get('is_available') == 'true'
        reason = request.POST.get('reason', '')
        
        if not date_str:
            messages.error(request, "No se proporcionó una fecha válida")
            return redirect('manage_availability', employee_id=employee.id)
            
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Actualizar o crear registro de disponibilidad
            availability, created = Availability.objects.update_or_create(
                employee=employee,
                date=selected_date,
                defaults={'is_available': is_available, 'reason': reason}
            )
            
            messages.success(request, f"Disponibilidad actualizada para {employee.name} el {selected_date}")
            
            # Redirect back to the same month view
            redirect_url = reverse('manage_availability', kwargs={'employee_id': employee.id} if employee_id else {})
            if year and month:
                redirect_url += f"?year={start_date.year}&month={start_date.month}"
            return redirect(redirect_url)
            
        except ValueError:
            messages.error(request, "Formato de fecha inválido")
            return redirect('manage_availability', employee_id=employee.id)
        except Exception as e:
            messages.error(request, f"Error actualizando disponibilidad: {str(e)}")
            return redirect('manage_availability', employee_id=employee.id)
    
    # Renderizar la plantilla con los datos necesarios
    return render(request, 'manage_availability.html', {
        'business': business,
        'employee': employee,
        'employees': employees,
        'calendar_data': calendar_data,
        'month_name': start_date.strftime('%B %Y'),
        'current_year': start_date.year,
        'current_month': start_date.month
    })

@login_required
def displayStaffCalendar(request):
    """
    Vista para mostrar el calendario de citas del personal con disponibilidad.
    """
    business = get_object_or_404(BusinessAccount, user=request.user)
    
    # Manejo de fechas
    date_str = request.GET.get('date')
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    except ValueError:
        current_date = date.today()
    
    # Calcular semana
    week_start = current_date - timedelta(days=current_date.weekday())
    week_end = week_start + timedelta(days=6)
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    
    # Obtener empleados con sus fotos
    employees = Employee.objects.filter(business=business).select_related('business')
    
    # Pre-cargar datos relacionados para mejor performance
    schedules = Schedule.objects.filter(
        employee__in=employees,
        is_active=True,
        start_date__lte=week_end
    ).filter(
        models.Q(end_date__isnull=True) | 
        models.Q(end_date__gte=week_start)
    ).select_related('employee')
    
    shifts = Shift.objects.filter(
        schedule__in=schedules
    ).select_related('schedule', 'schedule__employee')
    
    availabilities = Availability.objects.filter(
        employee__in=employees,
        date__range=[week_start, week_end]
    ).select_related('employee')
    
    appointments = Appointment.objects.filter(
        barber__in=employees,
        date__range=[week_start, week_end]
    ).order_by('date', 'time').select_related('barber', 'service')
    
    # Estructura de datos optimizada
    calendar_data = {
        'days': [{
            'date': week_start + timedelta(days=i),
            'day_name': (week_start + timedelta(days=i)).strftime('%a'),  # Abreviatura del día
            'full_day_name': (week_start + timedelta(days=i)).strftime('%A'),  # Nombre completo del día
            'day_number': (week_start + timedelta(days=i)).day,  # Número del día
            'month': (week_start + timedelta(days=i)).strftime('%b'),  # Abreviatura del mes
            'is_today': (week_start + timedelta(days=i)) == date.today(),
            'is_weekend': (week_start + timedelta(days=i)).weekday() >= 5  # Sábado o domingo
        } for i in range(7)],
        'employees': []
    }
    
    for employee in employees:
        employee_data = {
            'employee': employee,
            'days': [],
            'photo_url': employee.photo.url if employee.photo else None
        }
        
        for day in calendar_data['days']:
            day_shifts = [s for s in shifts if s.schedule.employee == employee and s.day_of_week == day['date'].weekday()]
            day_availability = next((a for a in availabilities if a.employee == employee and a.date == day['date']), None)
            day_appointments = [a for a in appointments if a.barber == employee and a.date == day['date']]
            
            # Ordenar citas por hora
            day_appointments.sort(key=lambda a: a.time)
            
            is_available = True
            if day_availability and not day_availability.is_available:
                is_available = False
            
            employee_data['days'].append({
                'date': day['date'],
                'shifts': day_shifts,
                'availability': day_availability,
                'appointments': day_appointments,
                'is_available': is_available,
                'appointment_count': len(day_appointments)
            })
        
        calendar_data['employees'].append(employee_data)
    
    context = {
        'business': business,
        'calendar_data': calendar_data,
        'week_start': week_start, 
        'week_end': week_end,
        'prev_week': prev_week,
        'next_week': next_week,
        'today': date.today(),
        'current_date': current_date,
        'has_employees': len(employees) > 0
    }
    
    return render(request, 'staff_calendar.html', context)


# View for managing appointments
@login_required
def manageAppointments(request):
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

@login_required
def createStaffAppointment(request):
    """
    Vista para crear una nueva cita.
    Utiliza el modelo Appointment existente.
    """
    from customer.models import Customer
    from django.db.models import Q
    import datetime
    
    business = get_object_or_404(BusinessAccount, user=request.user)

    # Manejar solicitudes AJAX para búsqueda de clientes
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Endpoint para buscar clientes
        if 'search_customer' in request.GET:
            query = request.GET.get('search_customer', '')
            customers = []
            
            if query:
                customers = Customer.objects.filter(
                    Q(first_name__icontains=query) | 
                    Q(last_name__icontains=query) | 
                    Q(user__email__icontains=query)
                )[:20]
            else:
                customers = Customer.objects.all().order_by('-id')[:50]
            
            results = []
            for customer in customers:
                results.append({
                    'id': customer.id,
                    'name': f"{customer.first_name} {customer.last_name}",
                    'email': customer.user.email
                })
            
            return JsonResponse({'customers': results})
        
        # Endpoint para obtener horarios disponibles
        elif 'get_available_times' in request.GET:
            employee_id = request.GET.get('employee_id')
            date_str = request.GET.get('date')
            
            if not employee_id or not date_str:
                return JsonResponse({'error': 'Faltan parámetros requeridos'}, status=400)
            
            try:
                employee = Employee.objects.get(id=employee_id)
                selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # 1. Verificar si el empleado tiene un horario para este día
                day_of_week = selected_date.weekday()
                shifts = Shift.objects.filter(
                    schedule__employee=employee,
                    schedule__is_active=True,
                    schedule__start_date__lte=selected_date,
                    day_of_week=day_of_week
                )
                
                # Filtrar por end_date si no es None
                shifts = shifts.filter(
                    Q(schedule__end_date__gte=selected_date) | 
                    Q(schedule__end_date__isnull=True)
                )
                
                if not shifts.exists():
                    return JsonResponse({
                        'available_times': [],
                        'message': f'El empleado no trabaja los {["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][day_of_week]}'
                    })
                
                # 2. Verificar disponibilidad específica para esa fecha
                availability = Availability.objects.filter(
                    employee=employee,
                    date=selected_date
                ).first()
                
                if availability and not availability.is_available:
                    return JsonResponse({
                        'available_times': [],
                        'message': f'El empleado no está disponible en esta fecha: {availability.reason}'
                    })
                
                # 3. Obtener citas existentes para ese día
                existing_appointments = Appointment.objects.filter(
                    barber=employee,
                    date=selected_date,
                    status='scheduled'
                )
                
                # 4. Generar slots de tiempo disponibles en intervalos de 30 minutos
                available_times = []
                
                for shift in shifts:
                    current_time = shift.start_time
                    end_time = shift.end_time
                    
                    # Crear slots de 30 minutos
                    while current_time < end_time:
                        # Verificar si este horario está disponible (no hay citas que se superpongan)
                        slot_end_time = (datetime.datetime.combine(datetime.date.today(), current_time) + 
                                        datetime.timedelta(minutes=30)).time()
                        
                        is_available = True
                        for appointment in existing_appointments:
                            app_end_time = (datetime.datetime.combine(datetime.date.today(), appointment.time) + 
                                          datetime.timedelta(minutes=appointment.duration_minutes)).time()
                            
                            # Verificar si hay superposición
                            if (current_time <= appointment.time < slot_end_time) or \
                               (appointment.time <= current_time < app_end_time):
                                is_available = False
                                break
                        
                        if is_available:
                            available_times.append(current_time.strftime('%H:%M'))
                        
                        # Avanzar al siguiente slot de 30 minutos
                        current_time = (datetime.datetime.combine(datetime.date.today(), current_time) + 
                                       datetime.timedelta(minutes=30)).time()
                
                return JsonResponse({
                    'available_times': available_times,
                    'message': '' if available_times else 'No hay horarios disponibles para esta fecha'
                })
                
            except Employee.DoesNotExist:
                return JsonResponse({'error': 'Empleado no encontrado'}, status=404)
            except ValueError:
                return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
        
        # Endpoint para obtener información del servicio
        elif 'get_service_info' in request.GET:
            service_id = request.GET.get('service_id')
            
            if not service_id:
                return JsonResponse({'error': 'ID de servicio no proporcionado'}, status=400)
            
            try:
                service = Service.objects.get(id=service_id)
                return JsonResponse({
                    'price': str(service.price),
                    'duration_minutes': 30  # Duración fija de 30 minutos
                })
            except Service.DoesNotExist:
                return JsonResponse({'error': 'Servicio no encontrado'}, status=404)

    # Procesamiento normal del formulario (no AJAX)
    # Prellenar con barbero y fecha si se proporcionan en la URL
    initial_data = {}
    if request.GET.get('barber'):
        initial_data['barber'] = request.GET.get('barber')
    if request.GET.get('date'):
        initial_data['date'] = request.GET.get('date')

    if request.method == 'POST':
        form = AppointmentForm(request.POST, initial=initial_data)
        if form.is_valid():
            appointment = form.save(commit=False)
            if appointment.barber.business != business:
                messages.error(request, 'El barbero seleccionado no pertenece a este negocio.')
                return redirect('manage_staff_appointments')
            
            # Verificar si se seleccionó un cliente existente
            customer = None
            customer_id = request.POST.get('selected_customer_id')
            
            if customer_id:
                try:
                    customer = Customer.objects.get(id=customer_id)
                except Customer.DoesNotExist:
                    pass
            
            try:
                # Establecer duración fija de 30 minutos
                appointment.duration_minutes = 30
                
                # Establecer precio basado en el servicio
                if appointment.service:
                    appointment.price = appointment.service.price
                
                # Usar la función create_appointment existente
                create_appointment(form, business, customer)
                messages.success(request, 'Cita creada exitosamente.')
                return redirect('manage_staff_appointments')
            except ValidationError as e:
                for error in e:
                    messages.error(request, error)
    else:
        form = AppointmentForm(initial=initial_data)

    # Filtrar barberos y servicios por negocio
    form.fields['barber'].queryset = Employee.objects.filter(business=business)
    form.fields['service'].queryset = Service.objects.filter(business=business)
    
    # Ocultar campos que se establecerán automáticamente
    form.fields['duration_minutes'].widget = forms.HiddenInput(attrs={'value': 30})
    form.fields['price'].widget.attrs['readonly'] = True

    context = {
        'business': business,
        'form': form,
        'action': 'create'
    }

    return render(request, 'staff_appointment_form.html', context)


@login_required
def manageStaffAppointments(request):
    """
    Vista para gestionar las citas del personal.
    Muestra una lista de todas las citas asociadas al negocio a través de sus empleados (barberos).
    """
    business = get_object_or_404(BusinessAccount, user=request.user)
    # Filtramos las citas por los barberos del negocio y las ordenamos por fecha y hora
    appointments = Appointment.objects.filter(
        barber__business=business
    ).select_related(
        'business',       # Relación ForeignKey directa en Appointment
        'barber',         # Relación ForeignKey a Employee
        'customer',       # Relación ForeignKey a Customer
        'service'         # Relación ForeignKey a Service
    ).order_by('-date', '-time')
    
    # Filtrar por estado si se proporciona
    status_filter = request.GET.get('status')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    # Filtrar por rango de fechas si se proporciona
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
    
    context = {
        'business': business,
        'appointments': appointments,
        'status_filter': status_filter,
        'start_date': start_date_str,
        'end_date': end_date_str
    }
    
    return render(request, 'staff_appointments.html', context)

@login_required
def editStaffAppointment(request, appointment_id):
    """
    Vista para editar una cita existente.
    Utiliza el modelo Appointment existente.
    """
    business = get_object_or_404(BusinessAccount, user=request.user)
    # Verificamos que la cita pertenezca a un barbero del negocio
    appointment = get_object_or_404(
        Appointment, 
        id=appointment_id, 
        barber__business=business
    )
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            updated_appointment = form.save(commit=False)
            # Verificamos que el barbero pertenezca al negocio
            if updated_appointment.barber.business != business:
                messages.error(request, 'El barbero seleccionado no pertenece a este negocio.')
                return redirect('manage_staff_appointments')
            
            # Aseguramos que el negocio no cambie
            updated_appointment.business = business
            updated_appointment.save()
            messages.success(request, 'Cita actualizada exitosamente.')
            return redirect('manage_staff_appointments')
    else:
        form = AppointmentForm(instance=appointment)
        # Filtrar barberos y servicios por negocio
        form.fields['barber'].queryset = Employee.objects.filter(business=business)
        form.fields['service'].queryset = Service.objects.filter(business=business)
    
    context = {
        'business': business,
        'form': form,
        'appointment': appointment,
        'action': 'edit'
    }
    
    return render(request, 'staff_appointment_form.html', context)

@login_required
def deleteStaffAppointment(request, appointment_id):
    """
    Vista para eliminar una cita.
    Utiliza el modelo Appointment existente.
    """
    business = get_object_or_404(BusinessAccount, user=request.user)
    # Verificamos que la cita pertenezca a un barbero del negocio
    appointment = get_object_or_404(
        Appointment, 
        id=appointment_id, 
        barber__business=business
    )
    
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, 'Cita eliminada exitosamente.')
        return redirect('manage_staff_appointments')
    
    context = {
        'business': business,
        'appointment': appointment
    }
    
    return render(request, 'confirm_delete_staff_appointment.html', context)

# Function to make appointment times only selectable during the selected barber's schedule
@require_GET
def get_available_hours(request):
    employee_id = request.GET.get('employee_id')
    date_str = request.GET.get('date')  # YYYY-MM-DD format

    try:
        employee = Employee.objects.get(id=employee_id)
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        weekday = selected_date.weekday()  # 0 = Monday
    except (Employee.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    # verify special availability
    availability = Availability.objects.filter(employee=employee, date=selected_date).first()
    if availability and not availability.is_available:
        return JsonResponse({'available_hours': []})  # Day marked as 'not available'

    # Obtain active shifts fot the day
    shifts = Shift.objects.filter(schedule__employee=employee, schedule__is_active=True,
                                  schedule__start_date__lte=selected_date,
                                  schedule__end_date__gte=selected_date,
                                  day_of_week=weekday)

    appointment_duration = timedelta(hours=1)
    available_hours = []

    # Obtain Appointments for that day
    existing_appointments = Appointment.objects.filter(
        barber=employee,
        date=selected_date,
        status='scheduled'
    )

    for shift in shifts:
        current_time = datetime.combine(selected_date, shift.start_time)
        shift_end_time = datetime.combine(selected_date, shift.end_time)

        while current_time + appointment_duration <= shift_end_time:
            end_time = current_time + appointment_duration
            overlap = existing_appointments.filter(
                time__gte=current_time.time(),
                time__lt=end_time.time()
            ).exists()

            if not overlap:
                available_hours.append(current_time.time().strftime('%H:%M'))

            current_time += appointment_duration

    return JsonResponse({'available_hours': available_hours})
 
@login_required
def update_appointment_status(request, appointment_id):
    from django.shortcuts import get_object_or_404
    from .models import Appointment
    
    appointment = get_object_or_404(Appointment, id=appointment_id)
    new_status = request.POST.get('status')
    
    if new_status in ['scheduled', 'completed', 'cancelled']:
        appointment.status = new_status
        appointment.save()
        
        # Para respuesta AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'new_status': appointment.status,
                'status_display': appointment.get_status_display()
            })
        
        # Para solicitudes normales
        messages.success(request, f'Appointment status updated to {new_status}')
        return redirect('manage_staff_appointments')
    
    return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)