# users/urls.py
from django.urls import path
from .views import RegisterView, CustomLoginView, CustomLogoutView, home

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    # URL pour la page d'accueil de test
    path('', home, name='home'),
]