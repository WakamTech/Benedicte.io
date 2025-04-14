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

class CustomUser(AbstractUser):
    """Modèle Utilisateur personnalisé utilisant l'email comme identifiant."""

    # Rendre le username non unique et optionnel (car on utilise l'email)
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=False, # <<< Non unique
        blank=True,   # <<< Peut être vide
        null=True,    # <<< Peut être null dans la DB
        help_text=_('Optionnel. 150 caractères ou moins.'),
        # validators=[username_validator], # Enlever validateurs si besoin
        error_messages={
            # 'unique': _("A user with that username already exists."), # Message plus nécessaire
        },
    )
    email = models.EmailField(
        _('adresse email'),
        unique=True, # <<< L'email DOIT être unique
        error_messages={
            'unique': _("Un utilisateur avec cette adresse email existe déjà."),
        },
    )

    USERNAME_FIELD = 'email' # Champ utilisé pour l'identification
    REQUIRED_FIELDS = [] # Champs requis lors de la création via createsuperuser (aucun autre que email/password)

    objects = CustomUserManager() # Utiliser notre manager personnalisé

    def __str__(self):
        return self.email