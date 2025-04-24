from django.shortcuts import render
from business.models import BusinessAccount

def showEidosHome(request): 
    return render(request, "home.html") 

def showContactInfo(request): 
    return render(request, "contact.html")

def searchBusiness(request):
    searchTerm = request.GET.get('searchBusiness')
    if searchTerm:
        businesses = BusinessAccount.objects.filter(name__icontains=searchTerm)
    else:
        businesses = BusinessAccount.objects.all()
    return render(request, 'search_business.html', {'searchTerm': searchTerm, 'businesses': businesses})

def register_choice(request):
    return render(request, 'register_choice.html')
