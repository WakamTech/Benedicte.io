# analysis/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse # Temporary
from .models import ScenarioRequest
from .forms import ScenarioRequestForm
from company.models import CompanyProfile # Need to link the profile

from .services import perform_analysis # Importez le service
import logging # Importer logging

logger = logging.getLogger(__name__) # Initialiser logger pour les vues

@login_required
def request_scenario_view(request):
    try:
        company_profile = request.user.company_profile
    except CompanyProfile.DoesNotExist:
        logger.warning(f"Utilisateur {request.user.id} a tenté d'accéder à la demande de scénario sans profil.")
        return redirect('company_profile_step')

    if request.method == 'POST':
        form = ScenarioRequestForm(request.POST)
        if form.is_valid():
            scenario_request = form.save(commit=False)
            scenario_request.user = request.user
            scenario_request.company_profile = company_profile
            scenario_request.status = 'pending' # Commence en attente
            scenario_request.save()
            logger.info(f"Demande de scénario {scenario_request.id} créée pour l'utilisateur {request.user.id}")

            # --- Déclenchement de l'analyse via le service ---
            # Exécution SYNCHRONE (l'utilisateur attend)
            logger.info(f"Déclenchement de l'analyse synchrone pour la demande {scenario_request.id}")
            analysis_successful = perform_analysis(scenario_request.id)
            logger.info(f"Fin de l'analyse synchrone pour la demande {scenario_request.id}. Succès: {analysis_successful}")

            # Rediriger vers la confirmation (qui montrera le statut final)
            return redirect(reverse('request_confirmation', args=[scenario_request.id]))

    else:
        form = ScenarioRequestForm()

    context = {
        'form': form,
        'step_title': "Étape 5: Quel est votre projet ?"
    }
    return render(request, 'analysis/request_scenario.html', context)

@login_required
def request_confirmation_view(request, request_id):
    # Simple confirmation page
    scenario_request = get_object_or_404(ScenarioRequest, id=request_id, user=request.user)
    context = {
        'request_id': scenario_request.id,
        'request_status': scenario_request.get_status_display(),
        'step_title': "Demande d'analyse soumise"
        }
    # In future, this might link to the dashboard:
    # context['dashboard_url'] = reverse('dashboard', args=[scenario_request.id])
    return render(request, 'analysis/request_confirmation.html', context)

# --- Optional: Processing View (if analysis takes time) ---
# @login_required
# def processing_view(request, request_id):
#     scenario_request = get_object_or_404(ScenarioRequest, id=request_id, user=request.user)
#     # You might use AJAX here to check status or just show a waiting message
#     context = {'request_id': scenario_request.id}
#     return render(request, 'analysis/processing.html', context)