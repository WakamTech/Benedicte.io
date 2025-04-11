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
    SCENARIO_TYPE_CHOICES = [
        ('global', 'Conseil Global'),
        ('product_launch', 'Lancement Produit'),
        ('cost_optimization', 'Optimisation Coûts'),
        # Add other predefined types if needed, or rely solely on description
        ('other', 'Autre (décrire)')
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
    # Option 1: Predefined type
    request_type = models.CharField(
        max_length=50,
        choices=SCENARIO_TYPE_CHOICES,
        default='global',
        verbose_name="Type de scénario"
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