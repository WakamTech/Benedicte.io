# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # Import Paginator classes
from analysis.models import ScenarioRequest # Importer le modèle d'analyse

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
    analysis_list = []
    page_obj = None # Initialiser page_obj

    if request.user.is_authenticated:
        # Récupérer TOUTES les analyses de l'utilisateur, triées par date (plus récentes d'abord)
        analysis_list = ScenarioRequest.objects.filter(user=request.user).order_by('-created_at')

        # Mettre en place la pagination
        paginator = Paginator(analysis_list, 10) # Afficher 10 analyses par page
        page_number = request.GET.get('page') # Récupérer le numéro de page depuis l'URL (?page=X)

        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            # Si page n'est pas un entier, afficher la première page.
            page_obj = paginator.page(1)
        except EmptyPage:
            # Si page est hors limites (ex. page 999), afficher la dernière page.
            page_obj = paginator.page(paginator.num_pages)

    # Le contexte inclut maintenant page_obj qui contient les analyses de la page courante
    # et les informations pour la navigation de pagination.
    context = {
        'is_authenticated': request.user.is_authenticated, # Passer explicitement si besoin hors auth context processor
        'username': request.user.username if request.user.is_authenticated else None,
        'page_obj': page_obj, # Passer l'objet Page au template
    }
    return render(request, 'home.html', context)