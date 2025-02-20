from django.shortcuts import render
from .models import Business

# Create your views here.
def dashboard(request, name):
    business = Business.objects.get(name=name)
    return render(request, "dashboard.html", {'business': business})

def services(request, name):
    business = Business.objects.get(name=name)
    return render(request, "services.html", {'business': business})

def profile(request, name):
    business = Business.objects.get(name=name)
    return render(request, "profile.html", {'business': business})