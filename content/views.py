# content/views.py
from django.shortcuts import render

def faq_view(request):
    # Plus tard, vous pourrez passer des données dynamiques si besoin
    context = {}
    return render(request, 'content/faq.html', context)

def contact_view(request):
    # Plus tard: ajouter un formulaire de contact ici
    context = {'step_title': "Contact"}
    return render(request, 'content/contact.html', context)

def privacy_policy_view(request):
    context = {'step_title': "Politique de Confidentialité"}
    return render(request, 'content/privacy_policy.html', context)

def terms_conditions_view(request):
    context = {'step_title': "Conditions Générales de Vente et d'Utilisation"}
    return render(request, 'content/terms_conditions.html', context)

def pricing_view(request):
    # Plus tard: récupérer les plans dynamiquement si besoin
    context = {'step_title': "Tarifs"}
    # Passer l'ID de prix Stripe au template pour le bouton d'inscription
    from django.conf import settings
    context['stripe_price_id'] = settings.STRIPE_PRICE_ID
    # Passer aussi la clé publiable si on utilise Stripe Elements ici
    # context['stripe_publishable_key'] = settings.STRIPE_PUBLISHABLE_KEY
    return render(request, 'content/pricing.html', context)

def legal_notice_view(request):
    context = {'step_title': "Mentions Légales"}
    return render(request, 'content/legal_notice.html', context)