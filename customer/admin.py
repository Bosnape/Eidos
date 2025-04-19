from django.contrib import admin
from django.contrib.auth import get_user_model
from customer.models import Customer

User = get_user_model()

# Crear una clase personalizada para administrar el modelo Customer
class CustomerAdmin(admin.ModelAdmin):
    
    def delete_model(self, request, obj):
        obj.user.delete()  
        super().delete_model(request, obj)  

    list_display = ('user', 'first_name', 'last_name', 'identification')  

    search_fields = ('first_name', 'last_name', 'identification')

admin.site.register(Customer, CustomerAdmin)