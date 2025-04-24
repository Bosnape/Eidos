from django.db import models
from eidos.models import Account
from django.conf import settings
from django.utils import timezone
import datetime

class BusinessAccount(models.Model):
    # Business model to store additional business information
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, default='')
    address = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='business/images/')
    user = models.OneToOneField(Account, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=20)
    
    instagram = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    tiktok = models.URLField(blank=True, null=True) 
   
    def __str__(self):
        return self.name

class RegistrationSession(models.Model):
    # Temporary storage for multi-phase registration
    session_key = models.CharField(max_length=100, unique=True)
    email = models.EmailField(max_length=100, default='')
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='business/images/')
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Session: {self.session_key}"
    
def get_default_business():
    return BusinessAccount.objects.first().id 

class Service(models.Model):
    business = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, default=get_default_business)  
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Employee(models.Model):
    business = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='employees', default=get_default_business)
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='employees/photos/', blank=True, null=True)
    job_description = models.TextField()
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.name} - {self.business.name}"

class PortfolioItem(models.Model):
    business = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='portfolio_items', default=get_default_business)
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='portfolio/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
# Mantenemos el modelo Appointment original
#  Appointment modified for integration
class Appointment(models.Model):
    business = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='appointments', default=get_default_business)
    date = models.DateField()
    time = models.TimeField()
    customer = models.ForeignKey('customer.Customer',  on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, null=True)
    customer_email = models.EmailField(max_length=100, blank=True, null=True)
    
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='appointments')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=[
        ("Cash", "Cash"), ("Card", "Card"), ("Online", "Online")
    ])
    duration_minutes = models.PositiveIntegerField(default=30)
    barber = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='appointments')
    
    customer_satisfaction = models.IntegerField(null=True, blank=True)
    repeat_customer = models.BooleanField(default=False)
    no_show = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='scheduled')

def clean(self):
    from django.core.exceptions import ValidationError

    if not self.time:
        raise ValidationError("Debes seleccionar una hora válida para la cita.")

    # Verificar que el empleado esté disponible en la fecha y hora seleccionada
    day_of_week = self.date.weekday()
    shifts = Shift.objects.filter(
        schedule__employee=self.barber,
        schedule__is_active=True,
        schedule__start_date__lte=self.date,
        schedule__end_date__gte=self.date,
        day_of_week=day_of_week
    )
    
    # Verificar disponibilidad específica para esa fecha
    availability = Availability.objects.filter(
        employee=self.barber,
        date=self.date
    ).first()
    
    if availability and not availability.is_available:
        raise ValidationError(f"El empleado no está disponible en esta fecha: {availability.reason}")
        
    # Verificar conflictos con otras citas
    end_time = (datetime.datetime.combine(datetime.date.today(), self.time) + 
                datetime.timedelta(minutes=self.duration_minutes)).time()

    conflicting_appointments = Appointment.objects.filter(
        barber=self.barber,
        date=self.date,
        status='scheduled'
    ).exclude(id=self.id)

    for appointment in conflicting_appointments:
        app_end_time = (datetime.datetime.combine(datetime.date.today(), appointment.time) + 
                       datetime.timedelta(minutes=appointment.duration_minutes)).time()
        
        if (self.time <= appointment.time < end_time) or \
           (appointment.time <= self.time < app_end_time):
            raise ValidationError("Hay un conflicto con otra cita programada.")

    def __str__(self):
        return f"Appointment for {self.customer_name} at {self.date} - {self.time}"    


class Schedule(models.Model):
    """Model for staff work schedules"""
    business = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, default=get_default_business)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='schedules')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.name}'s Schedule ({self.start_date} to {self.end_date or 'ongoing'})"

class Shift(models.Model):
    """Model for individual work shifts within a schedule"""
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='shifts')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.get_day_of_week_display()}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ['schedule', 'day_of_week']

class Availability(models.Model):
    """Model for recording when staff is not available"""
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.employee.name}: {status} on {self.date}"
    
    class Meta:
        verbose_name_plural = "Availabilities"
        unique_together = ['employee', 'date']

