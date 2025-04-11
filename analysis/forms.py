# analysis/forms.py
from django import forms
from .models import ScenarioRequest

class ScenarioRequestForm(forms.ModelForm):
    class Meta:
        model = ScenarioRequest
        # Fields the user needs to fill in this step
        fields = ['request_type', 'user_description']
        widgets = {
            'user_description': forms.Textarea(attrs={'rows': 4, 'placeholder': "Ex: Analyser l'impact de l'ouverture d'un nouveau point de vente à Lyon..."}),
        }
        labels = {
            'request_type': 'Quel type d\'analyse souhaitez-vous ?',
            'user_description': 'Décrivez plus précisément votre projet ou question (si "Autre" ou pour plus de détails) :',
        }