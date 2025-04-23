import uuid
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
from .models import BusinessAccount, RegistrationSession, Account, Service, Employee, PortfolioItem, Appointment
from .forms import BusinessInfoForm, BusinessUserForm, LoginForm, BusinessProfileForm, ServiceForm, SocialMediaForm, EmployeeForm, PortfolioItemForm
from .appointment_charts import *

from datetime import datetime, timedelta
from django.db.models import Sum, Avg
from openai import OpenAI
from dotenv import load_dotenv
import re

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
                annual_summary = getBusinessAnnualSummary(business)
                # Clear any existing monthly summary
                monthly_summary = None
            else:
                monthly_summary = getBusinessMonthlySummary(business)
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

def getBusinessMonthlySummary(business):
    """Get monthly summary of appointments for the business using openAI"""
    
    appointments = Appointment.objects.filter(business=business)
    
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

def getBusinessAnnualSummary(business):
    """Get month-by-month annual summary of appointments for the business using openAI"""
    
    appointments = Appointment.objects.filter(business=business)
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

