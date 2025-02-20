"""
URL configuration for eidosapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from django.conf.urls.static import static
from django.conf import settings

from eidos import views as eidos
from business import views as business

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', eidos.home, name="home"),
    path("contact/", eidos.contact, name="contact"), 
    path('business/', eidos.business, name="business"),
    path('get_started/', eidos.business_form, name="get_started"),
    path('get_started/welcome/', eidos.welcome, name="welcome"),
    path('dashboard/<str:name>/', business.dashboard, name="dashboard"),
    path('dashboard/<str:name>/services', business.services, name="services"),
    path('<str:name>/', business.profile, name="business_profile"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)