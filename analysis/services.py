# analysis/services.py
import requests
import base64
import json
import logging
from datetime import datetime
from django.conf import settings
from django.shortcuts import get_object_or_404
from openai import OpenAI # Import new OpenAI client

from .models import ScenarioRequest, ScenarioResult
from company.models import CompanyProfile, FinancialData, Charge, ProductService

# Setup basic logging
logger = logging.getLogger(__name__)

# --- INSEE API Service ---

def get_insee_access_token():
    """Obtient un token d'accès Bearer depuis l'API INSEE."""
    token_url = "https://api.insee.fr/token"
    auth_str = f"{settings.INSEE_CONSUMER_KEY}:{settings.INSEE_CONSUMER_SECRET}"
    auth_bytes = auth_str.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {'grant_type': 'client_credentials'}

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=10)
        response.raise_for_status() # Lève une exception pour les codes 4xx/5xx
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur d'obtention du token INSEE: {e}")
        return None

def fetch_latest_inflation_rate(token):
    """Récupère le dernier taux d'inflation annuel connu depuis l'API INSEE."""
    # Note: L'endpoint et l'ID exacts peuvent changer. A vérifier sur la doc INSEE.
    # Ceci est un exemple basé sur une structure possible.
    # IPC base 2015 ensemble des ménages - Identifiant série 001763821
    inflation_url = "https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/001763821?lastNObservations=1"
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(inflation_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Parser la réponse pour trouver la dernière valeur de glissement annuel (V Moyenne annuelle %)
        # La structure exacte dépend de l'API - ceci est une hypothèse
        last_observation = data.get('Series', [{}])[0].get('Obs', [{}])[-1]
        value = last_observation.get('OBS_VALUE') # Ceci n'est PAS le taux, c'est l'indice
        # Il faut calculer le glissement annuel à partir des indices, ou trouver l'API qui le donne directement.
        # Pour simplifier V1, on va retourner une valeur fixe ou None.
        # TODO: Implémenter le calcul réel ou trouver le bon endpoint/série pour le taux de glissement.
        logger.warning("Fonction fetch_latest_inflation_rate retourne une valeur placeholder.")
        # Placeholder:
        # return 2.5 # Retourne 2.5% comme placeholder
        return None # Plus prudent de retourner None si non implémenté
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur API INSEE (Inflation): {e}")
        return None
    except (IndexError, KeyError, TypeError) as e:
         logger.error(f"Erreur parsing réponse INSEE (Inflation): {e}")
         return None

def fetch_sector_growth_rate(token, sector_code):
    """Récupère le dernier taux de croissance pour un secteur donné (code NAF simplifié)."""
    # Note: Endpoint et série à adapter selon la granularité du code NAF et les données dispo.
    # Exemple: Indice CA Industrie - section C (fabrication) - ID fictif
    # Il faudra mapper votre SECTOR_CHOICES aux bons identifiants de séries INSEE.
    sector_series_map = {
        'C10': 'ID_SERIE_INSEE_AGRO',
        'G47': 'ID_SERIE_INSEE_COMMERCE_DETAIL',
        'J62': 'ID_SERIE_INSEE_INFO',
        'M71': 'ID_SERIE_INSEE_INGENIERIE',
        # ... autres mappings ...
        'other': None
    }
    series_id = sector_series_map.get(sector_code)
    if not series_id:
        logger.warning(f"Pas d'ID de série INSEE défini pour le code secteur: {sector_code}")
        return None

    growth_url = f"https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/{series_id}?lastNObservations=1"
    headers = {'Authorization': f'Bearer {token}'}

    try:
        response = requests.get(growth_url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # TODO: Parser la réponse pour trouver le dernier taux de croissance (glissement annuel ou trimestriel).
        # La structure exacte dépend de l'API.
        logger.warning(f"Fonction fetch_sector_growth_rate retourne une valeur placeholder pour {sector_code}.")
        # Placeholder:
        # if sector_code == 'J62': return 5.0 # Croissance 5% pour l'info
        # else: return 1.5 # Croissance 1.5% pour les autres
        return None # Plus prudent
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur API INSEE (Croissance Secteur {sector_code}): {e}")
        return None
    except (IndexError, KeyError, TypeError) as e:
         logger.error(f"Erreur parsing réponse INSEE (Croissance Secteur {sector_code}): {e}")
         return None


# --- OpenAI Service ---

# Initialize OpenAI Client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def format_internal_data(company_profile):
    """Formate les données internes pour le prompt OpenAI."""
    data_str = f"Entreprise: {company_profile.name}\n"
    data_str += f"Secteur: {company_profile.get_sector_code_display()} (Code: {company_profile.sector_code})\n"
    data_str += f"Marché: {company_profile.get_market_scope_display()}\n"
    data_str += f"Type d'activité: {company_profile.activity_type}\n\n"

    financials = FinancialData.objects.filter(company=company_profile).order_by('year')
    if financials:
        data_str += "Données Financières (CA Annuel):\n"
        for fin in financials:
            data_str += f" - Année {fin.year}: {fin.revenue} €\n"
        data_str += "\n"

    charges = Charge.objects.filter(company=company_profile)
    if charges:
        data_str += "Charges Annuelles Estimées:\n"
        for charge in charges:
            data_str += f" - {charge.get_type_display()} / {charge.description}: {charge.amount} €\n"
        data_str += "\n"

    products = ProductService.objects.filter(company=company_profile)
    if products:
        data_str += "Produits/Services Principaux (Contribution CA Annuel):\n"
        for prod in products:
            data_str += f" - {prod.name}: {prod.revenue_contribution} €\n"
        data_str += "\n"

    return data_str

def prepare_openai_prompt(internal_data_str, external_data, user_request_type, user_description):
    """Construit le prompt pour l'API OpenAI."""

    prompt = f"""
    **Contexte de l'Analyse :**
    Vous êtes un expert en analyse financière et stratégique pour les PME françaises.
    Analysez la situation de l'entreprise suivante et répondez à sa demande spécifique.
    Soyez concret, réaliste et basez vos projections sur les données fournies.

    **Données Internes de l'Entreprise :**
    {internal_data_str}

    **Données Externes Contextuelles (France) :**
    - Taux d'inflation annuel récent estimé: {external_data.get('inflation_rate', 'Non disponible')} %
    - Taux de croissance annuel récent estimé du secteur ({external_data.get('sector_code', 'N/A')}): {external_data.get('sector_growth_rate', 'Non disponible')} %
    (Note: Si une donnée externe est 'Non disponible', basez-vous sur des connaissances générales prudentes pour ce facteur).

    **Demande Spécifique de l'Utilisateur :**
    - Type d'analyse demandé: {user_request_type}
    - Description additionnelle: {user_description if user_description else "Aucune description additionnelle."}

    **Instructions pour la Réponse :**
    1.  **Synthèse Rapide :** Commencez par une brève synthèse de la situation actuelle perçue de l'entreprise (points forts/faibles basés sur les chiffres).
    2.  **Analyse Prospective (3 ans) :** En fonction de la demande, fournissez une projection simplifiée sur 3 ans (Année N+1, N+2, N+3). Incluez au minimum :
        - Prévision du Chiffre d'Affaires (CA) annuel. Expliquez brièvement l'hypothèse de croissance utilisée (lien avec croissance secteur, inflation, demande user...).
        - Prévision des Charges Totales annuelles (en appliquant l'inflation aux charges variables ou selon la demande).
        - Prévision de la Marge Brute Annuelle (CA - Charges Totales).
    3.  **Risques Majeurs (Top 2-3) :** Identifiez les 2 ou 3 risques principaux liés au scénario analysé ou à la situation générale (ex: dépendance client, hausse des coûts non maîtrisée, concurrence accrue...).
    4.  **Recommandations Clés (Top 2-3) :** Proposez 2 ou 3 recommandations concrètes et actionnables en réponse à la demande ou pour améliorer la situation. Codez chaque recommandation avec un niveau : [VERT] pour fort potentiel/conseillé, [ORANGE] pour potentiel modéré/prudence, [ROUGE] pour déconseillé/risque élevé.
    5.  **Format de Sortie IMPERATIF :** Structurez TOUTE votre réponse exclusivement en JSON valide comme suit :
        {{
          "synthese": "Votre synthèse ici...",
          "previsions_3_ans": [
            {{"annee": "N+1", "ca_prev": VALEUR_CA_1, "charges_prev": VALEUR_CHARGES_1, "marge_brute_prev": VALEUR_MARGE_1}},
            {{"annee": "N+2", "ca_prev": VALEUR_CA_2, "charges_prev": VALEUR_CHARGES_2, "marge_brute_prev": VALEUR_MARGE_2}},
            {{"annee": "N+3", "ca_prev": VALEUR_CA_3, "charges_prev": VALEUR_CHARGES_3, "marge_brute_prev": VALEUR_MARGE_3}}
          ],
          "hypotheses_previsions": "Brève explication des hypothèses clés utilisées (ex: croissance CA basée sur secteur + 1%, charges variables indexées sur inflation X%)...",
          "risques_cles": [
            "Description risque 1...",
            "Description risque 2...",
            "Description risque 3..."
          ],
          "recommandations": [
            {{"recommendation": "Description recommandation 1...", "niveau": "[VERT]"}},
            {{"recommendation": "Description recommandation 2...", "niveau": "[ORANGE]"}},
            {{"recommendation": "Description recommandation 3...", "niveau": "[ROUGE]"}}
          ]
        }}
    Ne retournez RIEN d'autre que ce JSON. Pas de texte avant ou après. Utilisez des nombres pour les valeurs numériques, pas de texte comme 'Non disponible'. Mettez 0 si la valeur est nulle.
    """
    return prompt

def call_openai_api(prompt):
    """Appelle l'API OpenAI et retourne la réponse brute."""
    try:
        # Utilisation de la nouvelle API client recommandée
        response = client.chat.completions.create(
            model="gpt-4o", # Ou "gpt-3.5-turbo" pour moins cher mais moins performant
            messages=[
                {"role": "system", "content": "Vous êtes un expert en analyse financière et stratégique pour PME."},
                {"role": "user", "content": prompt}
            ],
            # Demander explicitement du JSON peut aider (mais le prompt est déjà très directif)
            # response_format={ "type": "json_object" }, # Nécessite GPT-4 Turbo ou plus récent
            temperature=0.5, # Un peu de créativité mais pas trop pour la finance
            max_tokens=1500 # Ajuster si besoin
        )
        # Accéder au contenu de la réponse
        ai_response = response.choices[0].message.content
        return ai_response
    except Exception as e:
        logger.error(f"Erreur API OpenAI: {e}")
        return None

def parse_ai_response(ai_response_str):
    """Tente de parser la réponse textuelle de l'IA en JSON."""
    if not ai_response_str:
        return None
    try:
        # GPT peut parfois ajouter ```json ... ``` autour du JSON
        if ai_response_str.strip().startswith("```json"):
             ai_response_str = ai_response_str.strip()[7:-3].strip() # Enlever les marqueurs

        parsed_json = json.loads(ai_response_str)
        # TODO: Valider la structure du JSON ici si nécessaire
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing de la réponse JSON de l'IA: {e}")
        logger.error(f"Réponse reçue:\n{ai_response_str}")
        return None # Ou retourner un dict d'erreur


# --- Orchestration Service ---

def perform_analysis(scenario_request_id):
    """Orchestre tout le processus d'analyse pour une demande donnée."""
    try:
        scenario_request = get_object_or_404(ScenarioRequest, id=scenario_request_id)
        company_profile = scenario_request.company_profile

        # 1. Mise à jour statut
        scenario_request.status = 'processing'
        scenario_request.save()

        # 2. Récupérer Données Externes (INSEE)
        logger.info(f"Début récupération données externes pour demande {scenario_request_id}")
        insee_token = get_insee_access_token()
        inflation_rate = None
        sector_growth_rate = None
        if insee_token:
            inflation_rate = fetch_latest_inflation_rate(insee_token)
            sector_growth_rate = fetch_sector_growth_rate(insee_token, company_profile.sector_code)
        else:
            logger.warning("Impossible d'obtenir le token INSEE.")

        external_data = {
            'inflation_rate': inflation_rate,
            'sector_growth_rate': sector_growth_rate,
            'sector_code': company_profile.sector_code # Pour info dans le prompt
        }
        logger.info(f"Données externes récupérées: {external_data}")

        # 3. Formater Données Internes
        internal_data_str = format_internal_data(company_profile)

        # 4. Préparer le Prompt OpenAI
        prompt = prepare_openai_prompt(
            internal_data_str,
            external_data,
            scenario_request.get_request_type_display(),
            scenario_request.user_description
        )
        # logger.debug(f"Prompt OpenAI pour demande {scenario_request_id}:\n{prompt}") # Attention, peut être long

        # 5. Appeler OpenAI API
        logger.info(f"Appel API OpenAI pour demande {scenario_request_id}")
        ai_response_str = call_openai_api(prompt)

        # 6. Parser la Réponse et Sauvegarder le Résultat
        if ai_response_str:
            logger.info(f"Réponse reçue d'OpenAI pour demande {scenario_request_id}. Parsing...")
            parsed_result = parse_ai_response(ai_response_str)

            if parsed_result:
                # Créer ou mettre à jour ScenarioResult
                ScenarioResult.objects.update_or_create(
                    request=scenario_request,
                    defaults={'generated_data': parsed_result}
                )
                scenario_request.status = 'completed'
                scenario_request.save()
                logger.info(f"Analyse terminée avec succès pour demande {scenario_request_id}")
                return True # Succès
            else:
                # Erreur de parsing
                raise Exception("Erreur de parsing de la réponse de l'IA.")
        else:
            # Erreur API OpenAI
            raise Exception("Erreur lors de l'appel à l'API OpenAI.")

    except Exception as e:
        logger.error(f"Échec de l'analyse pour demande {scenario_request_id}: {e}")
        # Mettre à jour le statut en cas d'erreur
        try:
            scenario_request = ScenarioRequest.objects.get(id=scenario_request_id)
            scenario_request.status = 'failed'
            scenario_request.save()
        except ScenarioRequest.DoesNotExist:
            pass # La requête n'existait peut-être pas
        return False # Échec