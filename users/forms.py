# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model # Pour obtenir CustomUser
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import SetPasswordForm

CustomUser = get_user_model() # Récupère notre CustomUser

class CustomUserCreationForm(UserCreationForm):
    """Formulaire d'inscription personnalisé utilisant l'email."""
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email',) # Seulement demander l'email ici
        # Labels et help_texts en français
        labels = {
            'email': _('Adresse email'),
        }
        help_texts = {
            'password2': _('Entrez le même mot de passe que précédemment, pour vérification.'),
        }
        # Messages d'erreur personnalisés (optionnel, Django fournit déjà des traductions)
        # error_messages = { ... }

    # Surcharger __init__ si besoin de modifier les widgets ou autre
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     # Ex: Mettre un placeholder
    #     self.fields['email'].widget.attrs.update({'placeholder': _('votre.email@example.com')})


class CustomAuthenticationForm(AuthenticationForm):
    """Formulaire de connexion personnalisé utilisant l'email."""
    # Le champ 'username' d'AuthenticationForm sera utilisé pour l'email
    # car nous avons défini USERNAME_FIELD = 'email'
    username = forms.EmailField(
        label=_("Adresse email"),
        widget=forms.EmailInput(attrs={'autofocus': True, 'placeholder': _('votre.email@example.com')})
    )
    password = forms.CharField(
        label=_("Mot de passe"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': _('Votre mot de passe')}),
    )

    # Messages d'erreur personnalisés en français
    error_messages = {
        'invalid_login': _(
            "Veuillez entrer une adresse email et un mot de passe corrects. "
            "Attention, les deux champs peuvent être sensibles à la casse."
        ),
        'inactive': _("Ce compte est inactif."),
    }