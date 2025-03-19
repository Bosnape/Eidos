from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import BusinessAccount, RegistrationSession, Service, Employee, PortfolioItem

Account = get_user_model()

class BusinessInfoForm(forms.ModelForm):
    """Form for the first phase of business registration - business information"""  
    class Meta:
        model = RegistrationSession
        fields = ['name', 'logo', 'email', 'phone', 'address']

class BusinessUserForm(forms.ModelForm):
    """Form for the second phase of business registration - user credentials"""
    email = forms.EmailField(
        max_length=100, 
        required=True,
        widget=forms.EmailInput(attrs={
        'class': 'form-input w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none',
        'placeholder': 'your@email.com'
        })
    )
    
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
        'class': 'form-input w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none',
        'placeholder': '••••••••' 
        })
    )
    
    password2 = forms.CharField(
        label="Password confirmation",
        strip=False,
        widget=forms.PasswordInput(attrs={
        'class': 'form-input w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none',
        'placeholder': '••••••••'
        })
    )

    class Meta:
        model = Account
        fields = ['email']

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

class LoginForm(forms.Form):
    """Form for user login"""
    email = forms.EmailField(max_length=100, required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    
class BusinessProfileForm(forms.ModelForm):
    description = forms.CharField(
        max_length=500, 
        required=False,
        widget=forms.Textarea(attrs={'rows': 1})
    )
    
    class Meta:
        model = BusinessAccount
        fields = ['name', 'phone', 'email', 'address', 'description', 'logo']
        
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'price', 'available', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 1}),
            'price': forms.NumberInput(attrs={'step': '1'})
        }

class SocialMediaForm(forms.ModelForm):
    class Meta:
        model = BusinessAccount
        fields = ['instagram', 'facebook', 'twitter', 'tiktok']
        
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'photo', 'job_description', 'phone']

class PortfolioItemForm(forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ['title', 'description', 'image']