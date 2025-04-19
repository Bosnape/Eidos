from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from business.models import BusinessAccount, RegistrationSession, Service, Employee, PortfolioItem, Appointment, Account

class CustomerUserForm(forms.ModelForm):
    """Form for registering a customer (normal user)"""
    
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none',
            'placeholder': 'First Name'
        })
    )

    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none',
            'placeholder': 'Last Name'
        })
    )

    identification = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none',
            'placeholder': 'Identification Number'
        })
    )

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
        fields = ['first_name', 'last_name', 'identification', 'email']

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['date', 'time', 'service', 'barber', 'payment_method']

    def __init__(self, *args, **kwargs):
        super(AppointmentForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        # Customizing widgets for date and time
        self.fields['date'].widget = forms.DateInput(attrs={
            'class': 'form-control datepicker',
            'type': 'date',
        })
        self.fields['time'].widget = forms.TimeInput(attrs={
            'class': 'form-control timepicker',
            'type': 'time',
        })