# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.views import LoginView, LogoutView
import stripe # Importer stripe
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # Import Paginator classes
from analysis.models import ScenarioRequest # Importer le modèle d'analyse
from django.conf import settings
from .forms import CustomUserCreationForm, CustomAuthenticationForm
import logging
from django.urls import reverse
from django.contrib import messages
logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# Vue pour l'inscription (utilise une vue basée sur classe générique)
class RegisterView(CreateView):
    form_class = CustomUserCreationForm
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
    form_class = CustomAuthenticationForm
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

# Nouvelle vue pour initier le paiement
def start_stripe_checkout(request):
    # Vérifier si l'utilisateur est déjà connecté (optionnel, dépend du flux souhaité)
    # if request.user.is_authenticated:
    #     # Peut-être rediriger vers une page de gestion d'abonnement ou l'accueil ?
    #     logger.warning(f"Utilisateur déjà connecté {request.user.email} a tenté d'accéder à start_payment.")
    #     return redirect('home')

    # Vérifier que les clés et l'ID de prix sont configurés
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
         logger.error("Clé secrète Stripe ou Price ID non configuré dans les settings.")
         # Rediriger vers une page d'erreur ou l'accueil avec un message ?
         messages.error(request, "Erreur de configuration du paiement. Veuillez contacter le support.")
         return redirect('home') # Ou une page d'erreur dédiée

    # Construire les URLs de succès et d'annulation absolues
    # Attention: request.build_absolute_uri peut ne pas fonctionner correctement derrière certains proxys
    # Il est parfois plus sûr de construire l'URL à partir d'une variable d'environnement DOMAIN
    # DOMAIN = env('DOMAIN', default='http://127.0.0.1:8000') # Exemple dans settings
    # success_url = settings.DOMAIN + reverse('payment_success') + '?session_id={CHECKOUT_SESSION_ID}'
    # cancel_url = settings.DOMAIN + reverse('payment_cancelled')

    # Utilisation de build_absolute_uri pour commencer (plus simple en dev local)
    success_url = request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = request.build_absolute_uri(reverse('payment_cancelled'))

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'], # Accepter seulement la carte
            line_items=[
                {
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                },
            ],
            mode='subscription', # Important pour un abonnement récurrent
            success_url=success_url,
            cancel_url=cancel_url,
            # On laisse Stripe collecter l'email pour l'instant
            # customer_email=None, # Ne pas pré-remplir si l'utilisateur n'est pas connecté
            # Optionnel: Collecter l'adresse de facturation si nécessaire
            # billing_address_collection='required',
            # Optionnel: Permettre les codes promo
            # allow_promotion_codes=True,
        )
        # Rediriger l'utilisateur vers la page de paiement Stripe hébergée
        return redirect(checkout_session.url, code=303)

    except stripe.error.InvalidRequestError as e:
        logger.error(f"Erreur Stripe (Invalid Request) lors de la création de session Checkout: {e}")
        messages.error(request, f"Erreur de paiement : {e}. Vérifiez l'ID de Prix Stripe.")
        return redirect('home') # Ou page d'erreur
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création de session Checkout Stripe: {e}")
        messages.error(request, "Une erreur s'est produite lors de l'initialisation du paiement.")
        return redirect('home') # Ou page d'erreur

# --- Vues pour les redirections Stripe (placeholders) ---
def payment_success(request):
    session_id = request.GET.get('session_id')
    logger.info(f"Redirection succès Stripe avec session_id: {session_id}")
    # Ici, on NE crée PAS l'utilisateur. On attend le webhook.
    # On peut vérifier la session avec stripe.checkout.Session.retrieve(session_id) si besoin
    # pour afficher un message plus personnalisé, mais attention aux appels API inutiles.
    context = {
        'step_title': "Paiement Réussi",
        'message': "Merci pour votre inscription ! Votre paiement a été traité avec succès. Vous allez recevoir un email pour finaliser la création de votre compte et définir votre mot de passe."
        # 'session_id': session_id # Optionnel pour debug
    }
    return render(request, 'registration/payment_status.html', context)

def payment_cancelled(request):
    logger.info("Redirection annulation Stripe.")
    context = {
        'step_title': "Paiement Annulé",
        'message': "Votre processus d'inscription a été annulé. Vous n'avez pas été débité. Vous pouvez réessayer ou retourner à l'accueil.",
        'is_cancelled': True
    }
    return render(request, 'registration/payment_status.html', context)