from django.db import models
from eidos.models import Account

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
    
class Appointment(models.Model):
    business = models.ForeignKey(BusinessAccount, on_delete=models.CASCADE, related_name='appointments', default=get_default_business)
    date = models.DateField()
    time = models.TimeField()
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField(max_length=100) # Improved version: customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='appointments')
    
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='appointments') # service = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=[
        ("Cash", "Cash"), ("Card", "Card"), ("Online", "Online")
    ])
    duration_minutes = models.PositiveIntegerField()
    barber = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='appointments') # barber_name = models.CharField(max_length=100)
    
    customer_satisfaction = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    repeat_customer = models.BooleanField()
    no_show = models.BooleanField()
    status = models.CharField(max_length=20, choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='scheduled')

    def __str__(self):
        return f"Appointment for {self.customer_name} at {self.date} - {self.time}"