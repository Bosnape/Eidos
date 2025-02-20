from django.shortcuts import render, redirect
from .forms import BusinessForm
from business.models import Business

def home(request): 
    return render(request, "home.html") 
  
def contact(request): 
    return render(request, "contact.html")

def business(request):
    searchTerm = request.GET.get('searchBusiness')
    if searchTerm:
        businesses = Business.objects.filter(name__icontains=searchTerm)
    else:
        businesses = Business.objects.all()
    return render(request, 'business.html', {'searchTerm': searchTerm, 'businesses': businesses})

def business_form(request):
    if request.POST:
        form = BusinessForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
        return redirect('welcome')
        
    return render(request, "form.html", {'form': BusinessForm})

def welcome(request):
    return render(request, "welcome.html", {'business': Business.objects.last()})