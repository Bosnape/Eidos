from business.models import BusinessAccount

def user_type_context(request):
    user_type = None
    if request.user.is_authenticated:
        if hasattr(request.user, 'is_business') and request.user.is_business:
            user_type = 'business'
        elif hasattr(request.user, 'is_customer') and request.user.is_customer:
            user_type = 'customer'
    return {'user_type': user_type}

def business_user_context(request):
    business_user = None
    if request.user.is_authenticated and hasattr(request.user, 'is_business') and request.user.is_business:
        business_user = BusinessAccount.objects.get(user=request.user)
    return {'business_user': business_user}