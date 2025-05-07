import matplotlib.pyplot as plt
import matplotlib
import io
import base64
import numpy as np
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDay, TruncMonth, ExtractHour
from .models import Appointment

# Configure matplotlib to use a non-interactive backend
matplotlib.use('Agg')

# Define colors that match the site's theme
PRIMARY_COLOR = '#00a896'  # Teal - primary color
PRIMARY_DARK = '#007f6e'   # Darker teal
SECONDARY_COLORS = ['#00a896', '#007f6e', '#02c3b2', '#05d6c3', '#00897b', '#4BC0C0', '#9966FF']

def getImageBase64(plt):
    """Convert matplotlib plot to base64 string for embedding in HTML"""
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    # Encode the bytes to base64 string
    image_base64 = base64.b64encode(image_png).decode('utf-8')
    return f"data:image/png;base64,{image_base64}"

def generateTimeSlotChart(business):
    """Generate chart showing appointments by time slot for today"""
    
    today = datetime.today()
        
    # Get appointments for the specified date
    appointments = Appointment.objects.filter(business=business, date=today)
    
    # Extract hour from time and count appointments per hour
    hours = appointments.annotate(hour=ExtractHour('time')).values('hour').annotate(count=Count('id')).order_by('hour')
    
    # Prepare data for plotting
    hour_labels = [f"{hour}:00" for hour in range(8, 21)]  # 8 AM to 8 PM
    hour_counts = [0] * 13  # Initialize with zeros
    
    # Fill in actual data
    for slot in hours:
        hour = slot['hour']
        if 8 <= hour <= 20:  # Only include business hours
            hour_counts[hour - 8] = slot['count']
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    plt.bar(hour_labels, hour_counts, color=PRIMARY_COLOR)
    
    plt.title('Appointments by Time Slot', fontsize=18)
    plt.xlabel('Time of Day', fontsize=14)
    plt.ylabel('Number of Appointments', fontsize=14)
    plt.yticks(range(0, max(hour_counts) + 1, 1))
    plt.xticks(rotation=45)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image

def generateCustomerTypesChart(business, period='day'):
    """Generate chart showing new vs returning customers"""
    
    today = datetime.today()
    
    if period == 'day':
        # Daily view - pie chart for today
        # Get appointments for today
        appointments = Appointment.objects.filter(business=business, date=today)
        
        # Count new vs repeat customers
        new_customers = appointments.filter(repeat_customer=False).count()
        repeat_customers = appointments.filter(repeat_customer=True).count()
        
        # Prepare data for plotting
        labels = ['New Customers', 'Repeat Customers']
        counts = [new_customers, repeat_customers]
        colors = [PRIMARY_COLOR, PRIMARY_DARK]
        
        # Create the plot
        plt.figure(figsize=(10, 8))
        if sum(counts) > 0:  # Only create pie chart if there's data
            plt.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors,
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
            plt.legend(loc="upper right", bbox_to_anchor=(1.0, 0.9))
        else:
            # Create an empty pie chart with "No Data" label
            labels = ['No Data']
            counts = [1]
            colors = ['#dddddd']  # Light gray color for empty state
            plt.pie(counts, labels=labels, colors=colors,
                wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
            plt.legend(loc="upper right", bbox_to_anchor=(1.0, 0.9))
        
        plt.title('New vs Repeat Customers - Today', fontsize=18)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    elif period == 'month':
        # Monthly view - bar chart by day
        start_date = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        end_date = min(today, end_of_month)  # Limit to today
        
        # Get appointments for the current month
        month_appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date, 
            date__lte=end_date
        )
        
        # Prepare data for new vs returning clients by day
        days = [(start_date + timedelta(days=i)).day for i in range((end_date - start_date).days + 1)]
        new_clients = [0] * len(days)
        returning_clients = [0] * len(days)
        
        # Group by day and customer type
        for i, day_date in enumerate([(start_date + timedelta(days=i)) for i in range((end_date - start_date).days + 1)]):
            new = month_appointments.filter(
                date=day_date,
                repeat_customer=False
            ).count()
            
            returning = month_appointments.filter(
                date=day_date,
                repeat_customer=True
            ).count()
            
            new_clients[i] = new
            returning_clients[i] = returning
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        x = np.arange(len(days))
        width = 0.35
        
        plt.bar(x - width/2, new_clients, width, label='New Clients', color='#4BC0C0')
        plt.bar(x + width/2, returning_clients, width, label='Returning Clients', color='#9966FF')
        
        plt.xlabel('Day of Month', fontsize=14)
        plt.ylabel('Number of Clients', fontsize=14)
        plt.title(f'New vs Returning Clients - {today.strftime("%B %Y")}', fontsize=18)
        plt.xticks(x, days)
        plt.yticks(range(0, max(max(new_clients), max(returning_clients)) + 1, 1))
        plt.legend()
        plt.tight_layout()
        plt.grid(True, linestyle='--', alpha=0.3)
    
    else:  # year
        # Annual view - bar chart by month
        start_date = today.replace(month=1, day=1)
        
        # Get appointments for the current year
        year_appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date,
            date__lte=today
        )
        
        # Prepare data for new vs returning clients by month
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:today.month]
        new_clients = []
        returning_clients = []
        
        for month in range(1, today.month + 1):
            month_start = datetime(today.year, month, 1).date()
            if month < 12:
                month_end = datetime(today.year, month + 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(today.year, 12, 31).date()
            
            new = year_appointments.filter(
                date__gte=month_start,
                date__lte=month_end,
                repeat_customer=False
            ).count()
            
            returning = year_appointments.filter(
                date__gte=month_start,
                date__lte=month_end,
                repeat_customer=True
            ).count()
            
            new_clients.append(new)
            returning_clients.append(returning)
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        
        x = np.arange(len(months))
        width = 0.35
        
        plt.bar(x - width/2, new_clients, width, label='New Clients', color='#4BC0C0')
        plt.bar(x + width/2, returning_clients, width, label='Returning Clients', color='#9966FF')
        
        plt.xlabel('Month', fontsize=14)
        plt.ylabel('Number of Clients', fontsize=14)
        plt.title(f'New vs Returning Clients - {today.strftime("%Y")}', fontsize=18)
        plt.xticks(x, months)
        plt.legend()
        plt.tight_layout()
        plt.grid(True, linestyle='--', alpha=0.3)
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image

def generateRevenueChart(business, period='month'):
    """Generate line chart showing revenue by day for the current month or by month for the year"""
    
    today = datetime.today()
    
    if period == 'month':
        # Monthly view - revenue by day
        start_date = today.replace(day=1)
        # Limit end_date to today instead of end of month
        end_date = min(today, today.replace(month=today.month + 1, day=1) - timedelta(days=1))
        
        # Get appointments for the current month
        appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date, 
            date__lte=end_date
        )
        
        # Calculate revenue by day - using values first, then annotate for proper grouping
        revenue_by_day = appointments.values(
            day=TruncDay('date')
        ).annotate(
            total=Sum('price')
        ).order_by('day')
        
        # Prepare data for plotting
        # Only include days up to today
        days = [(start_date + timedelta(days=i)).day for i in range((end_date - start_date).days + 1)]
        revenue = [0] * len(days)
        
        # Fill in actual data
        for entry in revenue_by_day:
            day_idx = entry['day'].day - 1
            revenue[day_idx] = float(entry['total'])
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        plt.plot(days, revenue, marker='o', linestyle='-', color=PRIMARY_COLOR, linewidth=2, markersize=8)
        plt.title(f'Revenue by Day - {today.strftime("%B %Y")}', fontsize=18)
        plt.xlabel('Day of Month', fontsize=14)
        plt.xticks(days)
        plt.ylabel('Revenue ($)', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
    
    else:  # year
        # Yearly view - revenue by month
        start_date = today.replace(month=1, day=1)
        end_date = today
        
        # Get appointments for the current year
        appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date, 
            date__lte=end_date
        )
        
        # Calculate revenue by month - FIXED: using values first, then annotate for proper grouping
        revenue_by_month = appointments.values(
            month=TruncMonth('date')
        ).annotate(
            total=Sum('price')
        ).order_by('month')
        
        # Prepare data for plotting
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        revenue = [0] * 12
        
        # Fill in actual data
        for entry in revenue_by_month:
            month_idx = entry['month'].month - 1
            revenue[month_idx] = float(entry['total'])
        
        # Only include months up to the current month
        months = months[:today.month]
        revenue = revenue[:today.month]
        
        # Create the plot
        plt.figure(figsize=(12, 8))
        plt.plot(months, revenue, marker='o', linestyle='-', color=PRIMARY_COLOR, linewidth=2, markersize=8)
        plt.title(f'Monthly Revenue - {today.strftime("%Y")}', fontsize=18)
        plt.xlabel('Month', fontsize=14)
        plt.ylabel('Revenue ($)', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.tight_layout()
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image

def generateAppointmentsByDayChart(business):
    """Generate line chart showing appointments per day for the current month"""
    
    today = datetime.today()
    
    start_of_month = today.replace(day=1)
    if today.month == 12:
        end_of_month_full = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month_full = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    end_of_month = min(today, end_of_month_full)  # Limit to today
    
    # Get appointments for the current month
    appointments = Appointment.objects.filter(
        business=business, 
        date__gte=start_of_month, 
        date__lte=end_of_month
    )
    
    # Count appointments by day
    appointments_by_day = appointments.annotate(
        day=TruncDay('date')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Prepare data for plotting
    days = [(start_of_month + timedelta(days=i)).day for i in range((end_of_month - start_of_month).days + 1)]
    counts = [0] * len(days)
    
    # Fill in actual data
    for entry in appointments_by_day:
        day_idx = entry['day'].day - 1
        counts[day_idx] = entry['count']
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    plt.plot(days, counts, marker='o', linestyle='-', color=PRIMARY_DARK, linewidth=2, markersize=8)
    plt.title(f'Appointments per Day - {today.strftime("%B %Y")}', fontsize=18)
    plt.xlabel('Day of Month', fontsize=14)
    plt.xticks(days)
    plt.ylabel('Number of Appointments', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image

def generateTopServicesChart(business, period='month'):
    """Generate bar chart showing top services for the month or year"""
    
    today = datetime.today()
    
    if period == 'month':
        start_date = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        end_date = min(today, end_of_month)
        title_period = today.strftime("%B %Y")
    else:  # year
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        title_period = today.strftime("%Y")
    
    # Get appointments for the specified period
    appointments = Appointment.objects.filter(
        business=business, 
        date__gte=start_date, 
        date__lte=end_date
    )
    
    # Count appointments by service
    top_services = appointments.values(
        'service__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Prepare data for plotting
    service_names = []
    service_counts = []
    
    for service in top_services:
        service_names.append(service['service__name'])
        service_counts.append(service['count'])
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    if service_names:  # Only create bar chart if there's data
        bars = plt.bar(service_names, service_counts, color=SECONDARY_COLORS[:len(service_names)])
        
        # Add count labels on top of bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.0f}', ha='center', va='bottom')
    else:
        plt.text(0.5, 0.5, 'No service data available', horizontalalignment='center', verticalalignment='center')
    
    plt.title(f'Top Services - {title_period}', fontsize=18)
    plt.xlabel('Service', fontsize=14)
    plt.ylabel('Number of Bookings', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.grid(True, linestyle='--', alpha=0.3, axis='y')
    plt.tight_layout()
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image

def generateBarberPerformanceChart(business, period='month'):
    """Generate horizontal bar chart showing barber performance"""
    
    today = datetime.today()
    
    if period == 'month':
        start_date = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        end_date = min(today, end_of_month)  # Limit to today
        title_period = today.strftime("%B %Y")
    else:  # year
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        title_period = today.strftime("%Y")
    
    # Get appointments for the specified period
    appointments = Appointment.objects.filter(
        business=business, 
        date__gte=start_date, 
        date__lte=end_date
    )
    
    # Calculate revenue by barber
    barber_performance = appointments.values(
        'barber__name'
    ).annotate(
        revenue=Sum('price')
    ).order_by('-revenue')
    
    # Prepare data for plotting
    barber_names = []
    revenues = []
    
    for barber in barber_performance:
        barber_names.append(barber['barber__name'])
        revenues.append(float(barber['revenue']))
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    if barber_names:  # Only create bar chart if there's data
        # Create horizontal bar chart
        bars = plt.barh(barber_names, revenues, color=PRIMARY_COLOR)
        
        # Add revenue labels at the end of bars
        for i, bar in enumerate(bars):
            width = bar.get_width()
            plt.text(width + 5, bar.get_y() + bar.get_height()/2,
                    f'${width:.2f}', ha='left', va='center')
    else:
        plt.text(0.5, 0.5, 'No barber performance data available', horizontalalignment='center', verticalalignment='center')
    
    plt.title(f'Barber Performance - {title_period}', fontsize=18)
    plt.xlabel('Revenue ($)', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.3, axis='x')
    plt.tight_layout()
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image

def generateSatisfactionChart(business, period='month'):
    """Generate line chart showing average satisfaction over time"""
    
    today = datetime.today()
    
    if period == 'month':
        start_date = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        end_date = min(today, end_of_month)
        title_period = today.strftime("%B %Y")
        
        # Get appointments for the current month
        appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date, 
            date__lte=end_date,
            customer_satisfaction__gt=0
        )
        
        # Calculate average satisfaction by day
        satisfaction_by_day = appointments.annotate(
            day=TruncDay('date')
        ).values('day').annotate(
            avg=Avg('customer_satisfaction')
        ).order_by('day')
        
        # Prepare data for plotting
        days = [(start_date + timedelta(days=i)).day for i in range((end_date - start_date).days + 1)]
        satisfaction = [0] * len(days)
        
        # Fill in actual data
        for entry in satisfaction_by_day:
            day_idx = entry['day'].day - 1
            satisfaction[day_idx] = round(entry['avg'], 1)
        
        x_labels = days
        x_title = 'Day of Month'
    else:  # year
        start_date = today.replace(month=1, day=1)
        end_date = today
        title_period = today.strftime("%Y")
        
        # Get appointments for the current year
        appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date, 
            date__lte=end_date,
            customer_satisfaction__gt=0
        )
        
        # Calculate average satisfaction by month
        satisfaction_by_month = appointments.annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            avg=Avg('customer_satisfaction')
        ).order_by('month')
        
        # Prepare data for plotting
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        satisfaction = [0] * 12
        
        # Fill in actual data
        for entry in satisfaction_by_month:
            month_idx = entry['month'].month - 1
            satisfaction[month_idx] = round(entry['avg'], 1)
        
        # Only include months up to the current month
        months = months[:today.month]
        satisfaction = satisfaction[:today.month]
        
        x_labels = months
        x_title = 'Month'
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    plt.plot(x_labels, satisfaction, marker='o', linestyle='-', color=PRIMARY_COLOR, linewidth=2, markersize=8)
    plt.title(f'Average Customer Satisfaction - {title_period}', fontsize=18)
    plt.xlabel(x_title, fontsize=14)
    if period == 'month':
        plt.xticks(x_labels)
    plt.ylabel('Average Rating (1-5)', fontsize=14)
    plt.ylim(0, 5.5)  # Set y-axis limits for ratings 1-5
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image

def generateNoShowChart(business, period='month'):
    """Generate line chart showing no-show rate over time"""
    
    today = datetime.today()
    
    if period == 'month':
        start_date = today.replace(day=1)
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        end_date = min(today, end_of_month)  # Limit to today
        title_period = today.strftime("%B %Y")
        
        # Get all appointments for the current month
        all_appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date, 
            date__lte=end_date
        )
        
        # Count total appointments by day
        total_by_day = all_appointments.annotate(
            day=TruncDay('date')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Count no-show appointments by day
        no_shows_by_day = all_appointments.filter(
            no_show=True
        ).annotate(
            day=TruncDay('date')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        # Prepare data for plotting
        days = [(start_date + timedelta(days=i)).day for i in range((end_date - start_date).days + 1)]
        no_show_rates = [0] * len(days)
        
        # Create dictionaries for faster lookup
        total_dict = {entry['day'].day: entry['count'] for entry in total_by_day}
        no_show_dict = {entry['day'].day: entry['count'] for entry in no_shows_by_day}
        
        # Calculate no-show rate for each day
        for i, day in enumerate(days):
            total = total_dict.get(day, 0)
            no_shows = no_show_dict.get(day, 0)
            rate = (no_shows / total * 100) if total > 0 else 0
            no_show_rates[i] = round(rate, 1)
        
        x_labels = days
        x_title = 'Day of Month'
    else:  # year
        start_date = today.replace(month=1, day=1)
        end_date = today
        title_period = today.strftime("%Y")
        
        # Get all appointments for the current year
        all_appointments = Appointment.objects.filter(
            business=business, 
            date__gte=start_date, 
            date__lte=end_date
        )
        
        # Calculate no-show rate by month
        no_show_rates = []
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:today.month]
        
        for month in range(1, today.month + 1):
            month_start = datetime(today.year, month, 1).date()
            if month < 12:
                month_end = datetime(today.year, month + 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(today.year, 12, 31).date()
            
            total = all_appointments.filter(
                date__gte=month_start,
                date__lte=month_end
            ).count()
            
            no_shows = all_appointments.filter(
                date__gte=month_start,
                date__lte=month_end,
                no_show=True
            ).count()
            
            rate = (no_shows / total * 100) if total > 0 else 0
            no_show_rates.append(round(rate, 1))
        
        x_labels = months
        x_title = 'Month'
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    plt.plot(x_labels, no_show_rates, marker='o', linestyle='-', color=PRIMARY_DARK, linewidth=2, markersize=8)
    plt.title(f'No-show Rate - {title_period}', fontsize=18)
    plt.xlabel(x_title, fontsize=14)
    
    if period == 'month':
        plt.xticks(x_labels)
        
    plt.ylabel('No-show Rate (%)', fontsize=14)
    plt.ylim(0, max(no_show_rates) + 5 if no_show_rates else 10)  # Set y-axis limits
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    
    # Convert plot to base64 string
    chart_image = getImageBase64(plt)
    plt.close()
    
    return chart_image
