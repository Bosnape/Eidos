from django.db import models

# Create your models here.

class Business(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='business/images/')
    address = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name