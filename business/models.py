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