# analysis/models.py
from django.db import models
from django.conf import settings
from company.models import CompanyProfile # Link to the company data

class ScenarioRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('completed', 'Terminé'),
        ('failed', 'Échec'),
    ]
    # MISE À JOUR DES CHOIX (I.1)
    SCENARIO_TYPE_CHOICES = [
        ('new_product', 'Lancer un nouveau produit ou service'),
        ('new_market', 'Explorer un nouveau marché ou pays'),
        ('optimize_model', 'Optimiser un modèle économique existant'),
        ('funding', 'Simuler une levée de fonds ou un financement'),
        ('team', 'Recruter ou renforcer une équipe'),
        ('automation', 'Automatiser ou digitaliser un processus'),
        ('diversify', 'Diversifier l\'activité ou pivoter le business model'),
        ('external_change', 'Anticiper un changement externe (inflation, réglementation, concurrence)'),
        ('m_and_a', 'Préparer une fusion, acquisition ou partenariat stratégique'),
        ('other', 'Autre (champ libre)'),
        # On peut garder 'global' ou le supprimer si 'Autre' suffit
        # ('global', 'Conseil Global'), # A voir si on le garde
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scenario_requests'
    )
    # It might be good to link directly to the profile state used for this request
    company_profile = models.ForeignKey(
        CompanyProfile,
        on_delete=models.PROTECT, # Prevent deleting company data if analysis exists
        related_name='scenario_requests'
    )
    # Champ request_type utilisant les nouveaux choix
    request_type = models.CharField(
        max_length=50, # Laisser assez de marge pour les clés
        choices=SCENARIO_TYPE_CHOICES,
        # default='global', # Changer le défaut si 'global' est supprimé, ex: 'other' ?
        default='new_product', # Mettre un défaut pertinent
        verbose_name="Axe d'analyse principal" # Nouveau label plus précis ?
    )
    # Option 2: Free text description (as per "Quel est votre projet ?")
    user_description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Décrivez votre projet/question",
        help_text="Détaillez en quelques lignes votre projet ou la question spécifique à analyser."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Demande {self.id} pour {self.company_profile.name} par {self.user.username} ({self.get_status_display()})"

class ScenarioResult(models.Model):
    request = models.OneToOneField(
        ScenarioRequest,
        on_delete=models.CASCADE,
        related_name='result'
    )
    # Store results as JSON for flexibility, or define specific fields
    # Example using JSON:
    generated_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Données Générées (JSON)"
    )
    # Or specific fields:
    # forecast_summary = models.TextField(blank=True, null=True)
    # risks = models.TextField(blank=True, null=True)
    # recommendations = models.TextField(blank=True, null=True)
    # key_metrics_chart_data = models.JSONField(blank=True, null=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Résultats pour la demande {self.request.id}"