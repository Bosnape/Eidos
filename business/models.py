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