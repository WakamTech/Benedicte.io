# users/utils.py (Nouveau fichier)

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import PasswordResetTokenGenerator # On réutilise ce générateur
from django.urls import reverse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Créer une instance du générateur de token
account_activation_token_generator = PasswordResetTokenGenerator()

def send_set_password_email(user, request=None):
    """Envoie l'email pour définir le mot de passe après inscription via Stripe."""
    if not user or not user.email:
        logger.error("Tentative d'envoi d'email de définition de mot de passe sans utilisateur ou email.")
        return False

    # Générer le token et l'UID encodé en base64
    token = account_activation_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Construire l'URL de définition de mot de passe
    # Essayer d'utiliser le request pour construire l'URL absolue si possible
    if request:
         set_password_url = request.build_absolute_uri(
             reverse('create_password_confirm', kwargs={'uidb64': uid, 'token': token})
         )
    else:
         # Fallback si request n'est pas disponible (ex: depuis une tâche Celery)
         # Utiliser un domaine défini dans les settings
         domain = getattr(settings, 'APP_DOMAIN', 'localhost:8000') # Ajouter APP_DOMAIN à settings.py
         protocol = 'https' if not settings.DEBUG else 'http'
         set_password_url = f"{protocol}://{domain}{reverse('create_password_confirm', kwargs={'uidb64': uid, 'token': token})}"

    # Préparer le contexte pour le template email
    context = {
        'user': user,
        'set_password_url': set_password_url,
    }

    # Rendre le contenu de l'email depuis des templates
    subject = "Finalisez votre inscription Benedicte.io"
    # Corps de l'email en HTML
    html_message = render_to_string('emails/set_password_email.html', context)
    # Corps de l'email en texte brut (fallback)
    plain_message = render_to_string('emails/set_password_email.txt', context)

    try:
        send_mail(
            subject,
            plain_message, # Message texte
            settings.DEFAULT_FROM_EMAIL, # Expéditeur
            [user.email], # Destinataire(s)
            html_message=html_message, # Message HTML
            fail_silently=False,
        )
        logger.info(f"Email de définition de mot de passe envoyé à {user.email}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email de définition de mot de passe à {user.email}: {e}")
        return False