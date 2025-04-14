# users/urls.py
from django.urls import path
from .views import RegisterView, CustomLoginView, CustomLogoutView, home, start_stripe_checkout
from .views import payment_success, payment_cancelled # Importer les nouvelles vues
urlpatterns = [
    # path('register/', RegisterView.as_view(), name='register'),
    path('subscribe/start/', start_stripe_checkout, name='start_payment'), # NOUVELLE URL
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    # URL pour la page d'accueil de test
    path('', home, name='home'),
    path('subscribe/success/', payment_success, name='payment_success'),
    path('subscribe/cancelled/', payment_cancelled, name='payment_cancelled'),
]