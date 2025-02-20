from django import forms
from business.models import Business

class BusinessForm(forms.ModelForm):

    class Meta:
        model = Business
        fields = ['name', 'logo', 'address', 'email', 'phone']
        