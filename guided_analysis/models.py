# guided_analysis/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from analysis.models import ScenarioRequest # Lier la réponse à une demande d'analyse

# Modèle pour représenter les grands axes (optionnel, on peut aussi utiliser les choices)
# Si on utilise les choices de ScenarioRequest, ce modèle n'est pas nécessaire.
# Gardons simple pour l'instant et lions directement GuidingQuestion aux clés des choices.

class GuidingQuestion(models.Model):
    """Stocke une question spécifique pour guider l'analyse."""

    # Réutiliser les clés définies dans analysis.models.ScenarioRequest.SCENARIO_TYPE_CHOICES
    # ou copier/coller la liste ici si on préfère découpler. Copier est plus sûr si les choices changent.
    AXIS_CHOICES = [
        ('new_product', 'Lancer un nouveau produit ou service'),
        ('new_market', 'Explorer un nouveau marché ou pays'),
        ('optimize_model', 'Optimiser un modèle économique existant'),
        ('funding', 'Simuler une levée de fonds ou un financement'),
        ('team', 'Recruter ou renforcer une équipe'),
        ('automation', 'Automatiser ou digitaliser un processus'),
        ('diversify', 'Diversifier l\'activité ou pivoter le business model'),
        ('external_change', 'Anticiper un changement externe'),
        ('m_and_a', 'Préparer une fusion, acquisition ou partenariat'),
        # Note: Pas de question pour 'Autre (champ libre)' ici.
    ]

    RESPONSE_TYPE_CHOICES = [
        ('text', 'Texte Libre (court)'),
        ('textarea', 'Texte Libre (long)'),
        ('number', 'Nombre (entier ou décimal)'),
        ('boolean', 'Oui / Non'),
        ('choice', 'Choix Multiple (à définir)'), # Pourrait nécessiter un modèle lié pour les options
    ]

    axis_key = models.CharField(
        max_length=50,
        choices=AXIS_CHOICES,
        verbose_name="Axe d'Analyse Associé",
        help_text="La catégorie principale à laquelle cette question appartient."
    )
    question_text = models.TextField(
        verbose_name="Texte de la Question",
        help_text="La question telle qu'elle sera posée à l'utilisateur."
    )
    response_type = models.CharField(
        max_length=20,
        choices=RESPONSE_TYPE_CHOICES,
        default='text',
        verbose_name="Type de Réponse Attendue"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordre d'affichage",
        help_text="Ordre dans lequel afficher la question pour un axe donné (0, 1, 2...)."
    )
    is_required = models.BooleanField(
        default=False, # Rendre optionnel par défaut ? A discuter.
        verbose_name="Réponse obligatoire ?"
    )
    placeholder_text = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name="Texte d'aide (Placeholder)",
        help_text="Texte indicatif affiché dans le champ de réponse."
    )
    # Optionnel: Champ pour les options si response_type='choice'
    # response_options = models.JSONField(blank=True, null=True, verbose_name="Options (si type=choice)")

    class Meta:
        ordering = ['axis_key', 'order'] # Ordonner par axe, puis par ordre interne
        verbose_name = "Question Guidée"
        verbose_name_plural = "Questions Guidées"

    def __str__(self):
        return f"{self.get_axis_key_display()} - Q{self.order}: {self.question_text[:60]}..."


class UserResponse(models.Model):
    """Stocke la réponse d'un utilisateur à une question guidée pour une analyse spécifique."""
    scenario_request = models.ForeignKey(
        ScenarioRequest,
        on_delete=models.CASCADE, # Si la demande est supprimée, les réponses le sont aussi
        related_name='guided_responses',
        verbose_name="Demande d'Analyse Associée"
    )
    question = models.ForeignKey(
        GuidingQuestion,
        on_delete=models.CASCADE, # Si la question est supprimée (admin), la réponse aussi
        related_name='user_responses',
        verbose_name="Question Guidée"
    )
    # Stocker la réponse dans un champ texte, même si c'est un nombre ou booléen,
    # pour simplifier. La validation se fera au moment de la sauvegarde.
    answer_text = models.TextField(
        blank=True, null=True, # Permettre les réponses vides si non requis
        verbose_name="Réponse Fournie"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Assurer qu'un utilisateur ne répond qu'une fois à une question pour une demande donnée
        unique_together = ('scenario_request', 'question')
        ordering = ['scenario_request', 'question__order']
        verbose_name = "Réponse Utilisateur Guidée"
        verbose_name_plural = "Réponses Utilisateur Guidées"

    def __str__(self):
        return f"Réponse à Q{self.question.id} pour Demande {self.scenario_request.id}"