# analysis/forms.py
from django import forms
from .models import ScenarioRequest

class ScenarioRequestForm(forms.ModelForm):
    class Meta:
        model = ScenarioRequest
        fields = ['request_type', 'user_description']
        widgets = {
            # Garder le textarea pour la description
            'user_description': forms.Textarea(attrs={'rows': 4, 'placeholder': "Ex: Évaluer la rentabilité du lancement du produit X sur le marché Y..."}),
            # On pourrait utiliser des radios si la liste est courte, mais select est ok
            # 'request_type': forms.RadioSelect,
        }
        labels = {
            # NOUVEAU LABEL (I.2)
            'request_type': "Sélectionner le type d'analyse prospective souhaitez vous ?",
            # Label ajusté
            'user_description': 'Décrivez plus précisément votre projet ou question spécifique (obligatoire si "Autre") :',
        }

    # Optionnel: Ajouter une validation pour rendre 'user_description' obligatoire si 'request_type' est 'other'
    def clean(self):
        cleaned_data = super().clean()
        request_type = cleaned_data.get("request_type")
        user_description = cleaned_data.get("user_description")

        if request_type == 'other' and not user_description:
            self.add_error('user_description', "Veuillez fournir une description lorsque vous sélectionnez 'Autre'.")

        return cleaned_data 