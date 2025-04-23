from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import BusinessAccount, RegistrationSession, Service, Employee, PortfolioItem, Appointment
from .models import BusinessAccount, RegistrationSession, Service, Employee, PortfolioItem, Schedule, Shift, Availability, StaffAppointment

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


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['employee', 'start_date', 'end_date', 'is_active']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['day_of_week', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

class ShiftFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = Shift.objects.none()

ShiftFormSet = forms.modelformset_factory(
    Shift,
    form=ShiftForm,
    formset=ShiftFormSet,
    extra=7,
    max_num=7,
    can_delete=True
)

class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['employee', 'date', 'is_available', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class StaffAppointmentForm(forms.ModelForm):
    class Meta:
        model = StaffAppointment
        fields = ['employee', 'title', 'date', 'start_time', 'end_time', 'notes', 'status']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la cita'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Notas adicionales'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }