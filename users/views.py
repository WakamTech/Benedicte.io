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
from .utils import send_set_password_email # Importer la fonction d'envoi

from django.views.decorators.csrf import csrf_exempt # Important pour webhook
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import get_user_model # Pour récupérer CustomUser

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.forms import SetPasswordForm
from django.contrib import messages # Pour messages succès/erreur
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .forms import UserProfileUpdateForm # Importer le nouveau formulaire
account_activation_token_generator = PasswordResetTokenGenerator() # Réutiliser le générateur

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

CustomUser = get_user_model()

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

@csrf_exempt # Désactiver la vérification CSRF pour cette vue qui reçoit une requête externe
def stripe_webhook(request):
    """Ecoute les événements envoyés par Stripe."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    event = None
    
    # # --- LOGS DE DEBUG CRUCIAUX ---
    # logger.debug(f"--- Stripe Webhook Received ---")
    # logger.debug(f"Signature Header (sig_header): {sig_header}")
    # # Logguer seulement les premiers et derniers caractères du payload pour éviter des logs trop longs
    # payload_start = payload[:100] if isinstance(payload, bytes) else str(payload)[:100]
    # payload_end = payload[-100:] if isinstance(payload, bytes) else str(payload)[-100:]
    # logger.debug(f"Payload Start (type {type(payload)}): {payload_start}...")
    # logger.debug(f"Payload End: ...{payload_end}")
    # logger.debug(f"Endpoint Secret Used: {endpoint_secret[:5]}...{endpoint_secret[-5:]}") # Ne pas logger le secret entier
    # # --- FIN LOGS DE DEBUG ---

    # Vérifier si le secret est configuré
    if not endpoint_secret:
        logger.error("STRIPE_WEBHOOK_SECRET n'est pas configuré.")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        logger.info(f"Webhook Stripe reçu: Type={event['type']} ID={event['id']}")
    except ValueError as e:
        # Payload invalide
        logger.error(f"Webhook Stripe - Payload invalide: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Signature invalide
        logger.error(f"Webhook Stripe - Erreur de signature: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Webhook Stripe - Erreur inconnue lors de la construction de l'event: {e}")
        return HttpResponse(status=400)


    # Gérer l'événement checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        customer_email = session.get('customer_details', {}).get('email')
        stripe_customer_id = session.get('customer')
        stripe_subscription_id = session.get('subscription')

        logger.info(f"Checkout Session Completed: Email={customer_email}, CustID={stripe_customer_id}, SubID={stripe_subscription_id}")

        if not customer_email or not stripe_customer_id or not stripe_subscription_id:
            logger.error(f"Données manquantes dans l'événement checkout.session.completed: {session.id}")
            return HttpResponse(status=400) # Erreur dans les données reçues

        try:
            # Essayer de trouver l'utilisateur par email
            cleaned_email = customer_email.strip().strip("'").strip('"') if customer_email else None
            user, created = CustomUser.objects.get_or_create(
                email=cleaned_email,
                defaults={ # Valeurs à utiliser seulement si l'utilisateur est créé
                    'stripe_customer_id': stripe_customer_id,
                    'stripe_subscription_id': stripe_subscription_id,
                    'subscription_status': 'active',
                     # On le met actif, mais sans mot de passe utilisable pour l'instant
                    'is_active': True,
                    # On ne définit PAS de mot de passe ici.
                }
            )

            if created:
                # L'utilisateur vient d'être créé
                logger.info(f"Nouvel utilisateur créé via webhook: {customer_email} (ID: {user.id})")
                # *** TODO PHASE S3: Déclencher l'envoi de l'email "Définir votre mot de passe" ***
                # send_set_password_email(user) # <- Fonction à créer
                send_set_password_email(user, request=request)
                pass # Pour l'instant on ne fait rien de plus

            else:
                # L'utilisateur existait déjà (cas rare pour inscription, mais gérons-le)
                logger.warning(f"Webhook pour un utilisateur existant: {customer_email}. Mise à jour des infos Stripe.")
                user.stripe_customer_id = stripe_customer_id
                user.stripe_subscription_id = stripe_subscription_id
                user.subscription_status = 'active'
                # S'il était inactif pour une raison, on le réactive
                if not user.is_active:
                    user.is_active = True
                user.save()
                send_set_password_email(user, request=request)

        except Exception as e:
            logger.error(f"Erreur lors de la création/mise à jour de l'utilisateur via webhook: {e} pour email {customer_email}")
            # Que faire ? Renvoyer 500 pour que Stripe réessaie ? Ou 200 pour ne pas bloquer ?
            # Il vaut mieux logguer et renvoyer 200 pour éviter les boucles de webhook, mais surveiller les logs.
            # return HttpResponse(status=500)
            pass # On loggue l'erreur mais on renvoie 200 quand même

    # Gérer d'autres types d'événements si nécessaire (ex: paiement échoué, abonnement annulé)
    # elif event['type'] == 'invoice.payment_failed':
    #     # ... logique pour marquer l'abonnement comme inactif ...
    #     pass
    # elif event['type'] == 'customer.subscription.deleted':
    #      # ... logique pour marquer l'abonnement comme annulé ...
    #     pass

    # Accuser réception à Stripe
    return HttpResponse(status=200)


def create_password_confirm(request, uidb64=None, token=None):
    """Vue pour définir le mot de passe après inscription via Stripe."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and account_activation_token_generator.check_token(user, token):
        # Le lien est valide
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save() # Définit et sauvegarde le nouveau mot de passe
                # Optionnel: Marquer l'utilisateur comme pleinement actif si ce n'était pas déjà fait
                if not user.is_active: # Si on avait mis is_active=False initialement
                    user.is_active = True
                    user.save(update_fields=['is_active'])
                messages.success(request, "Votre mot de passe a été défini avec succès. Vous pouvez maintenant vous connecter.")
                return redirect('login')
            else:
                 messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
        else:
            form = SetPasswordForm(user)

        context = {
            'form': form,
            'step_title': "Définir votre mot de passe",
            'validlink': True,
        }
        return render(request, 'registration/create_password_form.html', context)
    else:
        # Lien invalide ou expiré
        messages.error(request, "Le lien de définition de mot de passe est invalide ou a expiré.")
        context = {
             'step_title': "Lien invalide",
             'validlink': False,
        }
        return render(request, 'registration/create_password_form.html', context)


@login_required
def user_profile_view(request):
    user = request.user
    update_form = UserProfileUpdateForm(instance=user) # Initialiser avec données user

    if request.method == 'POST':
        # Vérifier si le POST vient du formulaire de mise à jour de profil
        # (on pourrait ajouter un name="submit_profile" au bouton pour être plus sûr)
        if 'update_profile_submit' in request.POST: # Nom du bouton submit (à ajouter au template)
            update_form = UserProfileUpdateForm(request.POST, instance=user)
            if update_form.is_valid():
                update_form.save()
                messages.success(request, "Vos informations personnelles ont été mises à jour.")
                return redirect('user_profile') # Recharger la page profil
            else:
                messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")

    context = {
        'step_title': "Mon Profil",
        'user': user,
        'update_form': update_form, # Passer le formulaire au contexte
    }
    return render(request, 'users/profile.html', context)

@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        logger.warning(f"Demande de suppression de compte pour l'utilisateur: {user.email} (ID: {user.id})")

        # --- TODO: Logique d'annulation de l'abonnement Stripe ---
        # C'est une étape CRUCIALE pour éviter que l'utilisateur continue d'être facturé !
        # Il faut utiliser l'API Stripe pour annuler l'abonnement user.stripe_subscription_id
        # try:
        #    if user.stripe_subscription_id:
        #        stripe.Subscription.delete(user.stripe_subscription_id) # Ou .cancel() selon le comportement voulu
        #        logger.info(f"Abonnement Stripe {user.stripe_subscription_id} annulé pour {user.email}.")
        # except Exception as e:
        #     logger.error(f"Erreur lors de l'annulation de l'abonnement Stripe {user.stripe_subscription_id} pour {user.email}: {e}")
        #     # Que faire ? Empêcher la suppression ? Prévenir l'utilisateur ?
        #     messages.error(request, "Impossible d'annuler automatiquement votre abonnement Stripe. Veuillez le faire manuellement ou contacter le support.")
        #     return redirect('user_profile') # Ne pas supprimer le compte Django tant que l'abo est actif ?

        # Suppression de l'utilisateur Django (supprime aussi les données liées par CASCADE si configuré)
        try:
            user_email_for_log = user.email # Garder l'email pour le log
            user.delete()
            logout(request) # Déconnecter l'utilisateur
            messages.success(request, "Votre compte a été supprimé avec succès.")
            logger.info(f"Compte utilisateur supprimé avec succès: {user_email_for_log}")
            return redirect('home') # Rediriger vers l'accueil
        except Exception as e:
             logger.error(f"Erreur lors de la suppression du compte Django pour {user_email_for_log}: {e}")
             messages.error(request, "Une erreur s'est produite lors de la suppression de votre compte.")
             return redirect('user_profile')

    else:
        # Rediriger si la méthode n'est pas POST
        return redirect('user_profile')
    
@login_required
def redirect_to_stripe_billing_portal(request):
    """Redirige l'utilisateur vers son portail client Stripe."""
    user = request.user

    # Vérifier si l'utilisateur a un ID client Stripe
    if not user.stripe_customer_id:
        messages.error(request, "Impossible d'accéder à la gestion de l'abonnement (ID Client Stripe manquant).")
        logger.error(f"Tentative d'accès portail Stripe sans stripe_customer_id pour user {user.id}")
        return redirect('user_profile')

    # Définir l'URL de retour vers la page de profil après la session sur le portail
    # Utiliser build_absolute_uri pour être sûr
    return_url = request.build_absolute_uri(reverse('user_profile'))

    try:
        # Créer une session de portail client Stripe
        # Documentation: https://stripe.com/docs/api/customer_portal/sessions/create
        session = stripe.billing_portal.Session.create(
          customer=user.stripe_customer_id,
          return_url=return_url,
        )
        # Rediriger vers l'URL du portail
        return redirect(session.url, code=303)

    except Exception as e:
        logger.error(f"Erreur lors de la création de la session Portail Client Stripe pour user {user.id} (customer: {user.stripe_customer_id}): {e}")
        messages.error(request, "Une erreur s'est produite lors de l'accès à la gestion de votre abonnement. Veuillez réessayer plus tard.")
        return redirect('user_profile')