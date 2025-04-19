from django.db import models
from django.conf import settings


# Create your models here.

class Customer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    identification = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"