from django import forms

class LoginForm(forms.Form):
    """Form for user login"""
    email = forms.EmailField(max_length=100, required=True)
    password = forms.CharField(widget=forms.PasswordInput)