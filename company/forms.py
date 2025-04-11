# company/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import CompanyProfile, FinancialData, Charge, ProductService

class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        # Exclude fields managed automatically or linked
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}), # Make address field a bit bigger
        }

# FormSet for Financial Data - allows adding multiple years
FinancialDataFormSet = inlineformset_factory(
    CompanyProfile,           # Parent model
    FinancialData,            # Child model
    fields=('year', 'revenue'), # Fields to include in the formset
    extra=1,                  # Number of empty forms to display initially
    can_delete=True           # Allow deletion of existing entries
)

# FormSet for Charges - allows adding multiple charges
ChargeFormSet = inlineformset_factory(
    CompanyProfile,
    Charge,
    fields=('type', 'description', 'amount'),
    extra=1,
    can_delete=True
)

# FormSet for Products/Services - allows adding multiple products
ProductServiceFormSet = inlineformset_factory(
    CompanyProfile,
    ProductService,
    fields=('name', 'revenue_contribution'),
    extra=1,
    can_delete=True
)