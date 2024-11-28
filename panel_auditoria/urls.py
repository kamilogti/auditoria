# proyecto/urls.py
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('clientes/', include('clientes.urls')),
    path('login/', include('clientes.urls')),  # Incluye la URL de login
    path('', lambda request: redirect('login')),  # Redirige a la página de login como página principal
]
