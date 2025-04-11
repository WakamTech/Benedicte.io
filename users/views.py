# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView

# Vue pour l'inscription (utilise une vue basée sur classe générique)
class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login') # Redirige vers la page de connexion après succès

    def form_valid(self, form):
        user = form.save()
        # Optionnel : Connecter l'utilisateur directement après l'inscription
        # login(self.request, user)
        # return redirect('home') # Rediriger vers une page d'accueil si connexion directe
        return super().form_valid(form)

# Vue pour la connexion (utilise une vue basée sur classe intégrée)
class CustomLoginView(LoginView):
    form_class = AuthenticationForm
    template_name = 'registration/login.html'
    # L'URL de redirection après succès est définie dans settings.py (LOGIN_REDIRECT_URL)
    # ou peut être spécifiée ici avec success_url = reverse_lazy('ma_page_apres_login')

# Vue pour la déconnexion (utilise une vue basée sur classe intégrée)
class CustomLogoutView(LogoutView):
    # L'URL de redirection après succès est définie dans settings.py (LOGOUT_REDIRECT_URL)
    # ou peut être spécifiée ici avec next_page = reverse_lazy('ma_page_apres_logout')
    pass # La logique est gérée par la vue parente

# Optionnel : Une vue simple pour la page d'accueil ou une page de test
def home(request):
    return render(request, 'home.html')