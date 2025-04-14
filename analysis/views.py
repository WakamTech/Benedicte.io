# analysis/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse  # Temporary
from .models import ScenarioRequest
from .forms import ScenarioRequestForm
from company.models import CompanyProfile  # Need to link the profile
from django.conf import settings # Importer settings
from .services import perform_analysis, create_mock_analysis # Importer les deux fonctions
from .services import perform_analysis  # Importez le service
import logging  # Importer logging
from .models import ScenarioRequest, ScenarioResult # Assurez-vous que ScenarioResult est importé
import json
from django.contrib import messages # Importer le framework de messages Django
from datetime import datetime # Importez la CLASSE datetime depuis le MODULE datetime
from django.http import HttpResponse, Http404 # Importer HttpResponse, Http404
from .report_utils import generate_pdf_report, generate_excel_report # Importer les nouvelles fonctions

logger = logging.getLogger(__name__)  # Initialiser logger pour les vues


@login_required
def request_scenario_view(request):
    try:
        company_profile = request.user.company_profile
        # --- VÉRIFICATION DES DONNÉES (Point H) ---
        # Vérifier si des données minimales existent. Adaptez selon vos critères.
        # Exemple: au moins une donnée financière ET une charge ?
        has_financials = company_profile.financial_data.exists()
        has_charges = company_profile.charges.exists()
        has_products = company_profile.products_services.exists()

        # Définir ici les conditions minimales requises
        is_data_sufficient = has_financials and has_charges and has_products # Exemple simple

        if not is_data_sufficient:
            logger.warning(f"Utilisateur {request.user.id} a tenté une analyse sans données suffisantes.")
            # Afficher un message d'erreur à l'utilisateur
            messages.error(request, "Benedicte ne peut pas vous fournir d'analyse prospective sans aucune donnée d'entreprise (CA, Charges, Produits). Veuillez compléter les étapes précédentes.")
            # Rediriger vers la première étape manquante (logique à affiner)
            if not has_financials:
                 return redirect('company_financials_step')
            elif not has_charges:
                 return redirect('company_charges_step')
            else: # Manque produits
                 return redirect('company_products_step')
        # --- Fin Vérification ---

    except CompanyProfile.DoesNotExist:
        logger.warning(
            f"Utilisateur {request.user.id} a tenté d'accéder à la demande de scénario sans profil."
        )
        messages.warning(request, "Veuillez d'abord renseigner les informations de votre entreprise.")
        return redirect("company_profile_step")

    if request.method == "POST":
        form = ScenarioRequestForm(request.POST)
        if form.is_valid():
            scenario_request = form.save(commit=False)
            scenario_request.user = request.user
            scenario_request.company_profile = company_profile
            scenario_request.status = "pending"  # Commence en attente
            scenario_request.save()
            logger.info(
                f"Demande de scénario {scenario_request.id} créée pour l'utilisateur {request.user.id}"
            )

            # --- Déclenchement de l'analyse (Réelle ou Mock) ---
            if settings.USE_MOCK_ANALYSIS:
                # Utiliser la simulation
                logger.info(
                    f"Utilisation de la SIMULATION d'analyse pour la demande {scenario_request.id}"
                )
                create_mock_analysis(
                    scenario_request.id
                )  # Appelle la fonction de simulation
            else:
                # Utiliser le traitement réel (si les clés sont configurées et USE_MOCK_ANALYSIS=False)
                logger.info(
                    f"Déclenchement de l'analyse REELLE pour la demande {scenario_request.id}"
                )
                analysis_successful = perform_analysis(
                    scenario_request.id
                )  # Appelle la vraie fonction
                if not analysis_successful:
                    logger.error(
                        f"L'analyse REELLE a échoué pour la demande {scenario_request.id}. Vérifiez les logs précédents."
                    )
                    # Le statut sera mis à 'failed' par perform_analysis en cas d'erreur

            # Rediriger vers la confirmation (qui montrera le statut final)
            return redirect(reverse("request_confirmation", args=[scenario_request.id]))

    else:
        form = ScenarioRequestForm()

    context = {"form": form, "step_title": "Étape 5/5 : Quel est votre projet ?", 'prev_step_url': reverse('company_products_step'),}
    return render(request, "analysis/request_scenario.html", context)


@login_required
def request_confirmation_view(request, request_id):
    # Simple confirmation page
    scenario_request = get_object_or_404(
        ScenarioRequest, id=request_id, user=request.user
    )
    context = {
        "request_id": scenario_request.id,
        "request_status": scenario_request.get_status_display(),
        "step_title": "Demande d'analyse soumise",
    }
    # In future, this might link to the dashboard:
    # context['dashboard_url'] = reverse('dashboard', args=[scenario_request.id])
    return render(request, "analysis/request_confirmation.html", context)


# --- Optional: Processing View (if analysis takes time) ---
# @login_required
# def processing_view(request, request_id):
#     scenario_request = get_object_or_404(ScenarioRequest, id=request_id, user=request.user)
#     # You might use AJAX here to check status or just show a waiting message
#     context = {'request_id': scenario_request.id}
#     return render(request, 'analysis/processing.html', context)



@login_required
def display_dashboard(request, request_id):
    # Récupère la demande et vérifie que l'utilisateur est le propriétaire
    scenario_request = get_object_or_404(ScenarioRequest, id=request_id, user=request.user)

    # Essaye de récupérer le résultat associé
    try:
        scenario_result = scenario_request.result # Utilise le related_name 'result'
        analysis_data = scenario_result.generated_data # Récupère le JSON
    except ScenarioResult.DoesNotExist:
        scenario_result = None
        analysis_data = None # Pas encore de résultat

    # Prépare les données pour les graphiques (si les données existent)
    chart_data = None
    if analysis_data and 'previsions_3_ans' in analysis_data:
        labels = [item['annee'] for item in analysis_data['previsions_3_ans']]
        ca_data = [item.get('ca_prev', 0) for item in analysis_data['previsions_3_ans']]
        charges_data = [item.get('charges_prev', 0) for item in analysis_data['previsions_3_ans']]
        marge_data = [item.get('marge_brute_prev', 0) for item in analysis_data['previsions_3_ans']]

        chart_data = {
            'labels': json.dumps(labels), # Convertir en string JSON pour JS
            'ca_data': json.dumps(ca_data),
            'charges_data': json.dumps(charges_data),
            'marge_data': json.dumps(marge_data),
        }

    context = {
        'scenario_request': scenario_request,
        'scenario_result': scenario_result,
        'analysis_data': analysis_data, # Le JSON complet pour le template
        'chart_data': chart_data, # Données formatées pour Chart.js
        'step_title': f"Tableau de Bord - Analyse #{scenario_request.id}"
    }

    # Gérer les différents statuts de la requête
    if scenario_request.status == 'pending' or scenario_request.status == 'processing':
        # Si en cours, on peut afficher une page d'attente ou le dashboard avec un message
        # Pour l'instant, on affiche le dashboard mais on indique le statut
        context['is_processing'] = True
        # Option: Ajouter un header pour rafraîchir la page toutes les X secondes
        # response = render(request, 'analysis/dashboard.html', context)
        # response['Refresh'] = "15" # Rafraîchir toutes les 15 sec
        # return response

    elif scenario_request.status == 'failed':
        # Si échec, afficher un message d'erreur
        context['has_failed'] = True

    # Si completed (ou autre), affiche le dashboard normalement
    return render(request, 'analysis/dashboard.html', context)

@login_required
def download_report_view(request, request_id, format):
    """Gère le téléchargement du rapport PDF ou Excel."""
    scenario_request = get_object_or_404(ScenarioRequest, id=request_id, user=request.user)

    # Vérifier si l'analyse est terminée
    if scenario_request.status != 'completed':
        logger.warning(f"Tentative de téléchargement pour demande {request_id} non terminée (statut: {scenario_request.status}).")
        # Rediriger vers dashboard ou afficher une erreur ?
        # return redirect('dashboard', request_id=request_id)
        raise Http404("Le rapport n'est pas encore disponible ou l'analyse a échoué.")

    try:
        analysis_data = scenario_request.result.generated_data
    except ScenarioResult.DoesNotExist:
        logger.error(f"Aucun résultat trouvé pour la demande complétée {request_id}.")
        raise Http404("Les données d'analyse pour ce rapport sont introuvables.")

    filename_base = f"analyse_saas_{scenario_request.id}_{datetime.now().strftime('%Y%m%d')}"

    if format == 'pdf':
        buffer = generate_pdf_report(analysis_data, scenario_request)
        if buffer is None: # Gérer l'erreur de génération PDF
             logger.error(f"La génération PDF a échoué pour la demande {request_id}.")
             raise Http404("Erreur lors de la génération du rapport PDF.")
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename_base}.pdf"'
        logger.info(f"Téléchargement PDF pour demande {request_id} par utilisateur {request.user.id}")
        return response

    elif format == 'excel':
        buffer = generate_excel_report(analysis_data, scenario_request)
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response = HttpResponse(buffer, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename_base}.xlsx"'
        logger.info(f"Téléchargement Excel pour demande {request_id} par utilisateur {request.user.id}")
        return response

    else:
        logger.warning(f"Format de téléchargement inconnu demandé: {format} pour demande {request_id}.")
        raise Http404("Format de fichier non supporté.")