# users/urls.py
from django.urls import path
from .views import RegisterView, CustomLoginView, CustomLogoutView, home, start_stripe_checkout
from .views import payment_success, payment_cancelled # Importer les nouvelles vues
from .views import stripe_webhook, create_password_confirm 
from .views import user_profile_view # Importer la nouvelle vue
from .views import delete_account_view # Importer la nouvelle vue
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy # <<< Ajoutez reverse_lazy ici

urlpatterns = [
    # path('register/', RegisterView.as_view(), name='register'),
    path('subscribe/start/', start_stripe_checkout, name='start_payment'), # NOUVELLE URL
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    # URL pour la page d'accueil de test
    path('', home, name='home'),
    path('subscribe/success/', payment_success, name='payment_success'),
    path('subscribe/cancelled/', payment_cancelled, name='payment_cancelled'),
    path('stripe-webhook/', stripe_webhook, name='stripe_webhook'),
    path('create-password/<uidb64>/<token>/', create_password_confirm, name='create_password_confirm'),
    path('profile/', user_profile_view, name='user_profile'),
    path('profile/delete/', delete_account_view, name='delete_account'),
    path('profile/password_change/', auth_views.PasswordChangeView.as_view(template_name='users/password_change_form.html', success_url=reverse_lazy('password_change_done')), name='password_change'),
    path('profile/password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='users/password_change_done.html'), name='password_change_done'),
]