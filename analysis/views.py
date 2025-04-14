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

from guided_analysis.models import GuidingQuestion, UserResponse
from django.forms import formset_factory, CharField, Textarea, BooleanField, DecimalField, ChoiceField # Pour créer formulaire dynamique
from django.http import Http404

logger = logging.getLogger(__name__)  # Initialiser logger pour les vues

# --- Formulaire Dynamique pour les Réponses ---
# On crée une classe de base simple pour une réponse, puis on utilisera un formset
class BaseResponseForm(forms.Form):
    answer_text = CharField(
        widget=Textarea(attrs={'rows': 3, 'class': 'form-control form-control-sm'}),
        required=False # La validation 'required' sera gérée dynamiquement
    )
    # Ajouter d'autres types si besoin (number, boolean) mais Textarea peut tout contenir
    question_id = forms.IntegerField(widget=forms.HiddenInput()) # Pour savoir à quelle question on répond

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
    
    # Étape 1 de cette vue : Sélectionner l'axe (si pas encore fait)
    # On utilise la session pour stocker l'axe choisi temporairement
    selected_axis = request.session.get('selected_analysis_axis', None)
    axis_selection_form = ScenarioRequestForm(initial={'request_type': selected_axis}) # Pré-remplir si déjà choisi

    # Étape 2 de cette vue : Afficher/Traiter les questions guidées
    guiding_questions = []
    ResponseFormSet = None # Sera défini si un axe est choisi
    formset = None

    if selected_axis and selected_axis != 'other': # Pas de questions guidées pour 'Autre'
        guiding_questions = GuidingQuestion.objects.filter(axis_key=selected_axis).order_by('order')
        if guiding_questions:
            # Créer un FormSet Dynamique basé sur les questions récupérées
            ResponseFormSet = formset_factory(BaseResponseForm, extra=0) # extra=0 car on peuple avec les questions existantes

            # Préparer les données initiales pour le formset (une form par question)
            initial_data = [{'question_id': q.id} for q in guiding_questions]
            formset = ResponseFormSet(request.POST or None, initial=initial_data, prefix='response') # Utiliser un préfixe

    if request.method == 'POST':
        # Identifier quelle partie du formulaire est soumise
        if 'submit_axis' in request.POST: # L'utilisateur a choisi un axe
            axis_selection_form = ScenarioRequestForm(request.POST)
            if axis_selection_form.is_valid():
                selected_axis = axis_selection_form.cleaned_data['request_type']
                request.session['selected_analysis_axis'] = selected_axis
                 # Si 'Autre', on demande la description et on saute les questions guidées
                if selected_axis == 'other':
                     # Créer directement la demande et lancer l'analyse (ou aller à une étape de description libre)
                     # Pour l'instant, on redirige vers la même vue pour que l'utilisateur remplisse la description plus bas
                     logger.info(f"Axe 'Autre' choisi par {request.user.email}. Description requise.")
                     # Recréer le formset vide pour l'affichage
                     if ResponseFormSet:
                         formset = ResponseFormSet(initial=initial_data, prefix='response')
                     # Ne pas rediriger, laisser l'utilisateur remplir la description si besoin
                else:
                    # Recharger la page pour afficher les questions de l'axe choisi
                    # On recrée le formset basé sur le nouvel axe
                    guiding_questions = GuidingQuestion.objects.filter(axis_key=selected_axis).order_by('order')
                    initial_data = [{'question_id': q.id} for q in guiding_questions]
                    ResponseFormSet = formset_factory(BaseResponseForm, extra=0)
                    formset = ResponseFormSet(initial=initial_data, prefix='response') # Recréer le formset vide pour l'affichage
                    logger.info(f"Axe '{selected_axis}' choisi par {request.user.email}. Affichage questions.")
                    # Ne pas rediriger, on reste sur la page pour afficher les questions

        elif 'submit_responses' in request.POST and formset: # L'utilisateur a soumis les réponses aux questions guidées
             # On a besoin des infos de l'axe et de la description potentielle du formulaire d'axe
             # Il faudrait peut-être combiner les deux forms ou récupérer l'axe de la session
             final_axis_selection_form = ScenarioRequestForm(request.POST) # Récupérer aussi la description si besoin

             if formset.is_valid() and final_axis_selection_form.is_valid() :
                 # Créer la ScenarioRequest principale
                 scenario_request = final_axis_selection_form.save(commit=False)
                 scenario_request.user = request.user
                 scenario_request.company_profile = company_profile
                 scenario_request.status = 'pending'
                 # Assurer que request_type est bien celui de la session ou du formulaire
                 scenario_request.request_type = selected_axis
                 scenario_request.save()
                 logger.info(f"Demande de scénario {scenario_request.id} (axe: {selected_axis}) créée pour {request.user.email}")

                 # Sauvegarder les réponses guidées
                 for form in formset:
                     if form.is_valid(): # Vérifier chaque form du formset
                         question_id = form.cleaned_data.get('question_id')
                         answer = form.cleaned_data.get('answer_text')
                         if question_id and answer is not None: # Sauver seulement si réponse non vide? A décider.
                              try:
                                  question = GuidingQuestion.objects.get(pk=question_id)
                                  # Vérifier si la réponse est requise
                                  if question.is_required and not answer:
                                      # Normalement la validation du formset gère ça si 'required=True' est dynamique
                                      # Mais on peut ajouter une sécurité
                                      form.add_error('answer_text', 'Cette réponse est obligatoire.')
                                      raise forms.ValidationError("Erreur de validation interne.")

                                  UserResponse.objects.create(
                                       scenario_request=scenario_request,
                                       question=question,
                                       answer_text=answer
                                  )
                              except GuidingQuestion.DoesNotExist:
                                   logger.error(f"Question guidée ID {question_id} non trouvée lors de la sauvegarde des réponses pour SR {scenario_request.id}")
                              except forms.ValidationError:
                                   # Gérer l'erreur de validation levée
                                   pass # L'erreur sera ré-affichée dans le template

                 # Si des erreurs ont été ajoutées aux forms du formset, ne pas continuer
                 if not formset.is_valid(): # Revérifier après ajout d'erreurs potentiel
                     messages.error(request,"Veuillez corriger les erreurs dans les réponses.")
                 else:
                      # Nettoyer la session
                      if 'selected_analysis_axis' in request.session:
                          del request.session['selected_analysis_axis']

                      # --- Déclenchement de l'analyse ---
                      # La logique ici reste la même, perform_analysis devra être adapté en Q4
                      if settings.USE_MOCK_ANALYSIS:
                          create_mock_analysis(scenario_request.id)
                      else:
                          perform_analysis(scenario_request.id)

                      return redirect(reverse('request_confirmation', args=[scenario_request.id]))

             else:
                # Le formset ou le formulaire d'axe n'est pas valide
                messages.error(request,"Veuillez corriger les erreurs ci-dessous.")
                # L'erreur sera affichée dans le template

        # --- Gestion spéciale si l'axe est 'Autre' ---
        elif 'submit_other_description' in request.POST:
            final_axis_selection_form = ScenarioRequestForm(request.POST)
            if final_axis_selection_form.is_valid():
                 selected_axis = final_axis_selection_form.cleaned_data['request_type']
                 description = final_axis_selection_form.cleaned_data['user_description']
                 if selected_axis == 'other' and not description:
                      final_axis_selection_form.add_error('user_description',"La description est obligatoire pour le type 'Autre'.")
                      messages.error(request,"La description est obligatoire pour le type 'Autre'.")
                 else:
                     # Créer la ScenarioRequest directement
                     scenario_request = final_axis_selection_form.save(commit=False)
                     scenario_request.user = request.user
                     scenario_request.company_profile = company_profile
                     scenario_request.status = 'pending'
                     scenario_request.request_type = selected_axis # Devrait être 'other'
                     scenario_request.save()
                     logger.info(f"Demande de scénario {scenario_request.id} (axe: Autre) créée pour {request.user.email}")

                     # Nettoyer la session
                     if 'selected_analysis_axis' in request.session:
                         del request.session['selected_analysis_axis']

                     # --- Déclenchement de l'analyse ---
                     if settings.USE_MOCK_ANALYSIS: create_mock_analysis(scenario_request.id)
                     else: perform_analysis(scenario_request.id)

                     return redirect(reverse('request_confirmation', args=[scenario_request.id]))
            else:
                 messages.error(request,"Veuillez corriger les erreurs ci-dessous.")

    # else:
    #     form = ScenarioRequestForm()

    # --- Préparation Contexte ---
    context = {
        'step_title': f"Étape 5/5 : {dict(ScenarioRequest.SCENARIO_TYPE_CHOICES).get(selected_axis, 'Votre Projet')}" if selected_axis else "Étape 5/5 : Choix de l'Analyse",
        'axis_selection_form': axis_selection_form,
        'selected_axis': selected_axis,
        'guiding_questions': guiding_questions, # Liste des questions pour l'axe choisi
        'response_formset': formset, # Le formset pour les réponses
        'prev_step_url': reverse('company_products_step'),
    }
    # On utilisera un template différent pour afficher le formset
    return render(request, 'analysis/request_scenario_guided.html', context)


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