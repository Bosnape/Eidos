from django import forms
from django.contrib.auth import get_user_model
from .models import BusinessAccount, RegistrationSession, Service, Employee, PortfolioItem, Schedule, Shift, Availability, Appointment 

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

# Used to create/edit a Schedule
class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule  # Linked to the Schedule model
        fields = ['employee', 'start_date', 'end_date', 'is_active']  # Fields to include
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),  # Date picker for start_date
            'end_date': forms.DateInput(attrs={'type': 'date'}),  # Date picker for end_date
        }

# Defines a Shift within a schedule (e.g., Monday 9:00 AM – 5:00 PM).
class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift  # Linked to the Shift model
        fields = ['day_of_week', 'start_time', 'end_time']  # Fields to include
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),  # Time picker for start_time
            'end_time': forms.TimeInput(attrs={'type': 'time'}),  # Time picker for end_time
        }

# Manages multiple shifts (e.g., a week’s schedule) in a single form
class ShiftFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = Shift.objects.none()  # Start with an empty queryset

# Factory to create a formset for ShiftForm
#Used in create_schedule/edit_schedule views to handle bulk shift creation
ShiftFormSet = forms.modelformset_factory(
    Shift,                   # Model
    form=ShiftForm,          # Form class
    formset=ShiftFormSet,    # Custom formset logic
    extra=7,                 # Show 7 empty forms (one per weekday)
    max_num=7,               # Maximum of 7 shifts (one per day)
    can_delete=True          # Allow shifts to be deleted
)

# Tracks employee availability/unavailability on specific dates (e.g., time-off requests).
class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability  # Linked to the Availability model
        fields = ['employee', 'date', 'is_available', 'reason']  # Fields to include
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),  # Date picker for availability date
        }

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'barber', 'customer_name', 'customer_email', 'service', 
            'date', 'time', 'duration_minutes', 'price', 
            'payment_method', 'status'
        ]
        widgets = {
            'barber': forms.Select(attrs={'class': 'form-control'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente'}),
            'customer_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email del cliente'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '15', 'step': '15'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        } 