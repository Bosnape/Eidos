from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from business.models import BusinessAccount
from .forms import LoginForm

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

def loginView(request):
    # If the user is already authenticated, redirect appropriately
    if request.user.is_authenticated:
        if hasattr(request.user, 'businessaccount'):
            return redirect('business_dashboard')
        elif hasattr(request.user, 'customerprofile'):
            return redirect('userAppointments')
        else:
            return redirect('search_business')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "Welcome back!")

                if hasattr(user, 'businessaccount'):
                    return redirect('business_dashboard')

                elif hasattr(user, 'customer'):
                    return redirect('userAppointments')

                else:
                    messages.error(request, "This account is not associated with any valid profile.")
                    return redirect('search_business')

            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

@login_required
def logoutView(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('home')