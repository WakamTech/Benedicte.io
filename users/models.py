# users/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _ # Pour la traduction

class CustomUserManager(BaseUserManager):
    """
    Manager personnalisé pour le modèle User où l'email est l'identifiant unique
    au lieu du nom d'utilisateur.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un utilisateur avec l'email et le mot de passe donnés.
        """
        if not email:
            raise ValueError(_('L\'adresse email doit être renseignée'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crée et sauvegarde un superutilisateur avec l'email et le mot de passe donnés.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True) # Superuser doit être actif

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Le superutilisateur doit avoir is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)



class CustomUserManager(BaseUserManager):
    # ... (Manager reste inchangé) ...
    pass # Mettez le code du manager ici s'il n'y est pas déjà

class CustomUser(AbstractUser):
    username = models.CharField( # Inchangé
        _('username'), max_length=150, unique=False, blank=True, null=True,
        help_text=_('Optionnel. 150 caractères ou moins.'),
        error_messages={},
    )
    email = models.EmailField( # Inchangé
        _('adresse email'), unique=True,
        error_messages={
            'unique': _("Un utilisateur avec cette adresse email existe déjà."),
        },
    )

    # --- NOUVEAUX CHAMPS STRIPE ---
    stripe_customer_id = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="ID Client Stripe",
        help_text="ID unique du client sur Stripe."
    )
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="ID Abonnement Stripe",
        help_text="ID unique de l'abonnement actif sur Stripe."
    )
    # Statut simplifié pour commencer
    subscription_status = models.CharField(
        max_length=20, blank=True, null=True, default="inactive", # Défaut à inactif
        choices=[('active', 'Actif'), ('canceled', 'Annulé'), ('incomplete', 'Incomplet'), ('inactive', 'Inactif')],
        verbose_name="Statut Abonnement Stripe"
    )
    # --- FIN NOUVEAUX CHAMPS STRIPE ---

    # Rendre first_name et last_name optionnels si désiré (pour inscription rapide)
    first_name = models.CharField(_("prénom"), max_length=150, blank=True)
    last_name = models.CharField(_("nom"), max_length=150, blank=True)


    USERNAME_FIELD = 'email' # Inchangé
    REQUIRED_FIELDS = [] # Inchangé

    objects = CustomUserManager() # Inchangé

    def __str__(self): # Inchangé
        return self.email

    # Optionnel: Ajouter une propriété pour vérifier facilement si l'utilisateur est abonné actif
    @property
    def is_subscribed_active(self):
        return self.subscription_status == 'active'