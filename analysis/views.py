# analysis/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponse, Http404, JsonResponse # JsonResponse si API AJAX plus tard
from .models import ScenarioRequest, ScenarioResult
from .forms import ScenarioRequestForm # Garder pour le choix initial de l'axe
from company.models import CompanyProfile
from .services import perform_analysis, create_mock_analysis
from django.conf import settings
from guided_analysis.models import GuidingQuestion, UserResponse
from django.forms import formset_factory, CharField, Textarea, BooleanField, DecimalField, ChoiceField, IntegerField, HiddenInput # Pour créer formulaire dynamique
from django import forms # Import principal pour forms
from django.contrib import messages
import logging, json

logger = logging.getLogger(__name__)

# --- Formulaire de Base pour les Réponses Guidées ---
class BaseResponseForm(forms.Form):
    answer_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control form-control-sm'}),
        required=False # Sera défini dynamiquement
    )
    question_id = forms.IntegerField(widget=forms.HiddenInput())

@login_required
def request_scenario_view(request):
    """
    Gère l'Étape 5 :
    1. Sélection de l'axe d'analyse.
    2. Affichage et soumission des questions guidées (si axe != 'Autre').
    3. Affichage et soumission de la description libre (si axe == 'Autre' ou en complément).
    4. Lancement de l'analyse.
    """
    # --- Vérification Préalable du Profil et des Données ---
    try:
        company_profile = request.user.company_profile
        has_financials = company_profile.financial_data.exists()
        has_charges = company_profile.charges.exists()
        has_products = company_profile.products_services.exists()
        is_data_sufficient = has_financials and has_charges and has_products

        if not is_data_sufficient:
            logger.warning(f"Utilisateur {request.user.id} a tenté une analyse sans données suffisantes.")
            messages.error(request, "Benedicte ne peut pas vous fournir d'analyse prospective sans aucune donnée d'entreprise (CA, Charges, Produits). Veuillez compléter les étapes précédentes.")
            if not has_financials: return redirect('company_financials_step')
            elif not has_charges: return redirect('company_charges_step')
            else: return redirect('company_products_step')
    except CompanyProfile.DoesNotExist:
        logger.warning(f"Utilisateur {request.user.id} a tenté d'accéder à la demande de scénario sans profil.")
        messages.warning(request, "Veuillez d'abord renseigner les informations de votre entreprise.")
        return redirect('company_profile_step')

    # --- Gestion de l'État et Initialisation ---
    selected_axis = request.session.get('selected_analysis_axis', None)
    axis_choices_dict = dict(ScenarioRequest.SCENARIO_TYPE_CHOICES)
    selected_axis_label = axis_choices_dict.get(selected_axis) if selected_axis else None

    # Initialiser les variables pour le contexte
    axis_selection_form = None
    formset = None
    forms_with_questions = [] # Liste des paires (form, question)

    # --- Traitement de la Requête (POST ou GET) ---
    if request.method == 'POST':
        # --- CAS 1: Soumission du Choix de l'Axe ---
        if 'submit_axis' in request.POST:
            axis_selection_form = ScenarioRequestForm(request.POST)
            if axis_selection_form.is_valid():
                newly_selected_axis = axis_selection_form.cleaned_data['request_type']
                request.session['selected_analysis_axis'] = newly_selected_axis
                logger.info(f"Axe '{newly_selected_axis}' sélectionné par {request.user.email}. Rechargement.")
                # Rediriger vers GET pour afficher la suite
                return redirect(reverse('request_scenario'))
            else:
                # Le formulaire d'axe n'est pas valide (rare)
                messages.error(request, "Veuillez sélectionner un axe d'analyse valide.")
                # Laisser la vue continuer pour réafficher le formulaire avec erreurs

        # --- CAS 2: Soumission des Réponses aux Questions Guidées ---
        elif 'submit_responses' in request.POST:
            # Re-créer le formset avec les données POST pour validation
            if selected_axis and selected_axis != 'other':
                guiding_questions_qs = GuidingQuestion.objects.filter(axis_key=selected_axis).order_by('order')
                if guiding_questions_qs.exists():
                    ResponseFormSet = formset_factory(BaseResponseForm, extra=0)
                    initial_data = [{'question_id': q.id} for q in guiding_questions_qs]
                    formset = ResponseFormSet(request.POST, initial=initial_data, prefix='response')

                    # Appliquer la validation 'required' dynamiquement avant de valider
                    temp_questions_list = list(guiding_questions_qs)
                    for i, form in enumerate(formset):
                        try:
                            question = temp_questions_list[i]
                            if question.is_required:
                                form.fields['answer_text'].required = True
                        except IndexError: pass # Gérer l'erreur si index hors limites

            # Récupérer aussi le formulaire d'axe pour la description
            final_axis_form_check = ScenarioRequestForm(request.POST)

            if formset and formset.is_valid() and final_axis_form_check.is_valid():
                try:
                    # Sauvegarde de la demande et des réponses
                    scenario_request = final_axis_form_check.save(commit=False)
                    scenario_request.user = request.user
                    scenario_request.company_profile = company_profile
                    scenario_request.status = 'pending'
                    scenario_request.request_type = selected_axis # Utiliser l'axe de la session
                    scenario_request.save()
                    logger.info(f"Demande {scenario_request.id} (axe: {selected_axis}) créée pour {request.user.email}")

                    # Sauvegarder les réponses
                    for form_data in formset.cleaned_data:
                        question_id = form_data.get('question_id')
                        answer = form_data.get('answer_text', "") # Utiliser chaîne vide si None/absent
                        if question_id is not None:
                             try:
                                 question = GuidingQuestion.objects.get(pk=question_id)
                                 UserResponse.objects.update_or_create(
                                      scenario_request=scenario_request,
                                      question=question,
                                      defaults={'answer_text': answer}
                                 )
                             except GuidingQuestion.DoesNotExist:
                                  logger.error(f"Question ID {question_id} non trouvée lors sauvegarde pour SR {scenario_request.id}")

                    # Nettoyer session et lancer analyse
                    if 'selected_analysis_axis' in request.session: del request.session['selected_analysis_axis']
                    if settings.USE_MOCK_ANALYSIS: create_mock_analysis(scenario_request.id)
                    else: perform_analysis(scenario_request.id)

                    return redirect(reverse('request_confirmation', args=[scenario_request.id]))

                except Exception as e:
                     logger.error(f"Erreur sauvegarde réponses/requête pour axe {selected_axis}: {e}")
                     messages.error(request,"Une erreur interne est survenue lors de la sauvegarde.")
                     # Laisser la vue se re-rendre avec les formulaires/formset pour afficher les erreurs

            else:
                # Formset ou formulaire d'axe invalide
                logger.warning(f"Erreurs validation réponses pour axe {selected_axis}. Formset: {formset.errors if formset else 'N/A'}. AxisForm: {final_axis_form_check.errors}")
                messages.error(request,"Veuillez corriger les erreurs indiquées ci-dessous.")
                # Laisser la vue se re-rendre avec les formulaires/formset invalides

        # --- CAS 3: Soumission de la Description pour l'axe 'Autre' ---
        elif 'submit_other_description' in request.POST:
            axis_selection_form = ScenarioRequestForm(request.POST) # Valider ce formulaire
            if axis_selection_form.is_valid():
                 description = axis_selection_form.cleaned_data.get('user_description')
                 if axis_selection_form.cleaned_data.get('request_type') == 'other' and not description:
                      axis_selection_form.add_error('user_description',"La description est obligatoire pour le type 'Autre'.")
                      messages.error(request,"La description est obligatoire pour le type 'Autre'.")
                 else:
                     # Créer ScenarioRequest
                     scenario_request = axis_selection_form.save(commit=False)
                     scenario_request.user = request.user
                     scenario_request.company_profile = company_profile
                     scenario_request.status = 'pending'
                     scenario_request.request_type = 'other'
                     scenario_request.save()
                     logger.info(f"Demande {scenario_request.id} (axe: Autre) créée pour {request.user.email}")

                     if 'selected_analysis_axis' in request.session: del request.session['selected_analysis_axis']
                     if settings.USE_MOCK_ANALYSIS: create_mock_analysis(scenario_request.id)
                     else: perform_analysis(scenario_request.id)

                     return redirect(reverse('request_confirmation', args=[scenario_request.id]))
            else:
                 messages.error(request,"Veuillez corriger les erreurs ci-dessous.")
                 # Laisser la vue se re-rendre avec le formulaire invalide


    # --- Préparation pour Affichage (GET ou re-rendu après POST invalide) ---

    # Si axis_selection_form n'a pas été défini par un POST invalide, l'initialiser pour GET
    if axis_selection_form is None:
         axis_selection_form = ScenarioRequestForm(initial={'request_type': selected_axis})

    # Si formset n'a pas été défini par un POST invalide, l'initialiser pour GET si applicable
    if formset is None and selected_axis and selected_axis != 'other':
        guiding_questions_qs = GuidingQuestion.objects.filter(axis_key=selected_axis).order_by('order')
        if guiding_questions_qs.exists():
            ResponseFormSet = formset_factory(BaseResponseForm, extra=0)
            initial_data = [{'question_id': q.id} for q in guiding_questions_qs]
            formset = ResponseFormSet(initial=initial_data, prefix='response')
            # Appliquer 'required' dynamiquement pour l'affichage GET
            temp_questions_list = list(guiding_questions_qs)
            forms_with_questions = [] # Recalculer pour le contexte
            for i, form in enumerate(formset):
                 try:
                     question = temp_questions_list[i]
                     if question.is_required:
                         form.fields['answer_text'].required = True
                     forms_with_questions.append({'form': form, 'question': question})
                 except IndexError: pass

    # --- Contexte Final ---
    context = {
        'step_title': f"Étape 5/5 : {selected_axis_label}" if selected_axis_label else "Étape 5/5 : Choix de l'Analyse",
        'axis_selection_form': axis_selection_form,
        'selected_axis': selected_axis,
        'selected_axis_label': selected_axis_label,
        'forms_with_questions': forms_with_questions, # La liste de paires (form, question)
        'response_formset': formset, # Passer aussi le formset pour le management form et les erreurs globales
        'prev_step_url': reverse('company_products_step'),
    }
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