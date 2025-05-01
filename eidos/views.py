from django.shortcuts import render
from business.models import BusinessAccount
from django.http import JsonResponse
from django.db.models import Q

def showEidosHome(request): 
    return render(request, "home.html") 

def showContactInfo(request): 
    return render(request, "contact.html")

def searchBusiness(request):
    searchTerm = request.GET.get('searchBusiness')
    if searchTerm:
        # Enhanced search using Q objects across multiple fields
        businesses = BusinessAccount.objects.filter(
            Q(name__icontains=searchTerm) | 
            Q(description__icontains=searchTerm) |
            Q(address__icontains=searchTerm)
        ).distinct()
    else:
        businesses = BusinessAccount.objects.all()
    return render(request, 'search_business.html', {'searchTerm': searchTerm, 'businesses': businesses})

def searchBusinessAjax(request):
    """Handle AJAX search requests from the navbar"""

    searchTerm = request.GET.get('searchBusiness')
    results = []
    
    if searchTerm and len(searchTerm) >= 2:
        # Use Q objects to search across multiple fields
        businesses = BusinessAccount.objects.filter(
            Q(name__icontains=searchTerm) | 
            Q(description__icontains=searchTerm) |
            Q(address__icontains=searchTerm)
        ).distinct()[:5]  # Limit to 5 results
        
        for business in businesses:
            # Include logo URL in the response
            logo_url = business.logo.url if business.logo else ''
            results.append({
                'name': business.name,
                'address': business.address,
                'logo_url': logo_url
            })
    
    return JsonResponse({'businesses': results})

def register_choice(request):
    return render(request, 'register_choice.html')
