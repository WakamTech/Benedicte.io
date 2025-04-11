# company/models.py
from django.db import models
from django.conf import settings # To link to the User model

class CompanyProfile(models.Model):
    # Link to the user who owns this profile
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )
    # Company details
    name = models.CharField(max_length=255, verbose_name="Nom de l'entreprise")
    address = models.TextField(blank=True, null=True, verbose_name="Adresse")
    sector = models.CharField(max_length=100, blank=True, null=True, verbose_name="Secteur d'activité")
    activity_type = models.CharField(max_length=255, blank=True, null=True, verbose_name="Type de produits ou services")
    MARKET_CHOICES = [
        ('local', 'Local'),
        ('national', 'National'),
        ('international', 'International'),
    ]
    market_scope = models.CharField(
        max_length=20,
        choices=MARKET_CHOICES,
        blank=True,
        null=True,
        verbose_name="Marché"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil de {self.name} ({self.user.username})"

class FinancialData(models.Model):
    # Link to the company profile
    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name='financial_data'
    )
    year = models.PositiveIntegerField(verbose_name="Année")
    revenue = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Chiffre d'Affaires (CA)")
    # Add other key financial metrics if needed later

    class Meta:
        unique_together = ('company', 'year') # Ensure only one entry per company per year
        ordering = ['-year'] # Show most recent first

    def __str__(self):
        return f"{self.company.name} - {self.year}: CA {self.revenue}€"

class Charge(models.Model):
    # Link to the company profile
    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name='charges'
    )
    CHARGE_TYPE_CHOICES = [
        ('fixed', 'Fixe'),
        ('variable', 'Variable'),
    ]
    type = models.CharField(
        max_length=10,
        choices=CHARGE_TYPE_CHOICES,
        verbose_name="Type de charge"
    )
    description = models.CharField(max_length=255, verbose_name="Description (ex: Loyer, Salaires, Matières premières)")
    # Using DecimalField for monetary values is best practice
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Montant Annuel Estimé (€)") # Or monthly? Specify clearly. Assuming Annual.

    def __str__(self):
        return f"{self.company.name} - Charge {self.type}: {self.description} ({self.amount}€)"

class ProductService(models.Model):
    # Link to the company profile
    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name='products_services'
    )
    name = models.CharField(max_length=255, verbose_name="Nom du Produit / Service")
    # Represent contribution as a percentage or absolute value? Let's use absolute value for now.
    revenue_contribution = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Contribution au CA Annuel (€)",
        help_text="Montant du CA généré par ce produit/service sur la dernière année complète."
    )

    def __str__(self):
        return f"{self.company.name} - Produit/Service: {self.name} ({self.revenue_contribution}€)"