# analysis/services.py
import requests
import base64
import json
import logging
import time # Pour simuler un délai
from datetime import datetime
from django.conf import settings
from django.shortcuts import get_object_or_404
from openai import OpenAI , AuthenticationError

from .models import ScenarioRequest, ScenarioResult
from company.models import CompanyProfile, FinancialData, Charge, ProductService

# Setup basic logging
logger = logging.getLogger(__name__)

# --- INSEE API Service (Placeholders/TODO) ---

def get_insee_access_token():
    """Obtient un token d'accès Bearer depuis l'API INSEE."""
    # Utiliser les clés depuis les settings (lues depuis .env)
    consumer_key = getattr(settings, 'INSEE_CONSUMER_KEY', None)
    consumer_secret = getattr(settings, 'INSEE_CONSUMER_SECRET', None)

    if not consumer_key or not consumer_secret:
        logger.error("Clés API INSEE non configurées dans les settings.")
        return None

    token_url = "https://api.insee.fr/token"
    auth_str = f"{consumer_key}:{consumer_secret}"
    auth_bytes = auth_str.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

    headers = { 'Authorization': f'Basic {auth_b64}', 'Content-Type': 'application/x-www-form-urlencoded' }
    data = {'grant_type': 'client_credentials'}

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        token = response.json().get('access_token')
        logger.info("Token d'accès INSEE obtenu avec succès.")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur d'obtention du token INSEE: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'obtention du token INSEE: {e}")
        return None

def fetch_latest_inflation_rate(token):
    """Récupère le dernier taux d'inflation annuel connu depuis l'API INSEE."""
    if not token: return None
    # TODO: Trouver le bon endpoint et ID de série INSEE pour le taux d'inflation annuel
    # et implémenter le parsing correct de la réponse.
    inflation_url = "https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/001763821?lastNObservations=1" # ID Exemple IPC
    headers = {'Authorization': f'Bearer {token}'}
    try:
        # response = requests.get(inflation_url, headers=headers, timeout=10)
        # response.raise_for_status()
        # data = response.json()
        # parsed_rate = ... # Logique de parsing ici
        logger.warning("Fonction fetch_latest_inflation_rate retourne une valeur placeholder.")
        return 2.5 # Placeholder
    except Exception as e:
        logger.error(f"Erreur lors de la récupération/parsing de l'inflation INSEE: {e}")
        return None

def fetch_sector_growth_rate(token, sector_code):
    """Récupère le dernier taux de croissance pour un secteur donné."""
    if not token or not sector_code: return None
    # TODO: Mapper les sector_code internes aux ID de séries INSEE et parser la réponse.
    sector_series_map = { 'J62': 'ID_SERIE_INFO_EXAMPLE', } # Mappings incomplets
    series_id = sector_series_map.get(sector_code)
    if not series_id:
        logger.warning(f"Pas d'ID de série INSEE mappé pour le secteur: {sector_code}. Utilisation d'un placeholder.")
        return 3.0 # Placeholder générique

    growth_url = f"https://api.insee.fr/series/BDM/V1/data/SERIES_BDM/{series_id}?lastNObservations=1"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        # response = requests.get(growth_url, headers=headers, timeout=10)
        # response.raise_for_status()
        # data = response.json()
        # parsed_growth = ... # Logique de parsing ici
        logger.warning(f"Fonction fetch_sector_growth_rate retourne une valeur placeholder pour {sector_code}.")
        if sector_code == 'J62': return 5.0 # Placeholder spécifique
        return 3.0 # Placeholder générique
    except Exception as e:
        logger.error(f"Erreur lors de la récupération/parsing croissance secteur INSEE {sector_code}: {e}")
        return None

# --- Service OpenAI ---

# Initialisation Globale du Client (si clé dans settings)
# Si la clé peut changer (via config admin par ex.), initialiser dans call_openai_api
openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
client = None
if openai_api_key:
    try:
        client = OpenAI(api_key=openai_api_key)
        logger.info("Client OpenAI initialisé avec la clé des settings.")
    except Exception as e:
         logger.error(f"Erreur initialisation client OpenAI depuis settings: {e}")
else:
     logger.warning("Clé API OpenAI non trouvée dans les settings. L'analyse réelle échouera.")


# --- Fonctions de Formatage des Données ---

def format_internal_data(company_profile):
    """Formate les données internes de base pour le prompt OpenAI."""
    if not company_profile: return "Données de profil entreprise non disponibles.\n"
    data_str = f"Entreprise: {company_profile.name or 'Non spécifié'}\n"
    data_str += f"Secteur: {company_profile.get_sector_code_display() or 'Non spécifié'} (Code: {company_profile.sector_code or 'N/A'})\n"
    data_str += f"Marché: {company_profile.get_market_scope_display() or 'Non spécifié'}\n"
    data_str += f"Type d'activité: {company_profile.activity_type or 'Non spécifié'}\n"

    products = ProductService.objects.filter(company=company_profile)
    if products.exists():
         data_str += "\nProduits/Services Principaux et Description:\n"
         for prod in products:
             desc = f" ({prod.description})" if prod.description else ""
             contrib = f" - Contrib. CA: {prod.revenue_contribution} €" if prod.revenue_contribution is not None else ""
             data_str += f" - {prod.name or 'Produit/Service Anonyme'}{desc}{contrib}\n"

    financials = FinancialData.objects.filter(company=company_profile).order_by('year')
    if financials.exists():
        data_str += "\nDonnées Financières (CA Annuel):\n"
        for fin in financials: data_str += f" - Année {fin.year}: {fin.revenue} €\n"

    charges = Charge.objects.filter(company=company_profile)
    if charges.exists():
        data_str += "\nCharges Annuelles Estimées:\n"
        for charge in charges: data_str += f" - {charge.get_type_display()} / {charge.description}: {charge.amount} €\n"

    if not financials.exists() and not charges.exists() and not products.exists():
         data_str += "\nATTENTION: Peu de données internes détaillées fournies.\n"

    return data_str

def format_guided_responses(scenario_request):
    """Récupère et formate les réponses aux questions guidées pour le prompt."""
    responses = scenario_request.guided_responses.select_related('question').order_by('question__order')
    if not responses.exists():
        # Si l'axe n'est pas 'Autre', c'est peut-être un problème qu'il n'y ait pas de réponse.
        if scenario_request.request_type != 'other':
             logger.warning(f"Aucune réponse guidée trouvée pour SR {scenario_request.id} (axe: {scenario_request.request_type}), alors que ce n'est pas 'Autre'.")
             return "Aucune réponse spécifique fournie par l'utilisateur pour cet axe.\n"
        else:
             return "" # Pas de section réponse si c'est l'axe 'Autre'

    response_str = "Détails Spécifiques Fournis par l'Utilisateur (Réponses aux Questions Guidées) :\n"
    for resp in responses:
        answer = resp.answer_text if resp.answer_text else "(Non renseigné)"
        response_str += f"- Q: {resp.question.question_text}\n"
        response_str += f"  R: {answer}\n"
    response_str += "\n" # Ajoute une ligne vide après les réponses
    return response_str


# --- Préparation du Prompt et Appel API ---

def prepare_openai_prompt(internal_data_str, external_data, scenario_request):
    """Construit le prompt pour l'API OpenAI en intégrant les réponses guidées."""
    user_request_type_display = scenario_request.get_request_type_display()
    guided_responses_str = format_guided_responses(scenario_request)
    user_description = scenario_request.user_description if scenario_request.user_description else None

    prompt = f"""
    **Contexte de l'Analyse :**
    Vous êtes un expert en analyse financière et stratégique pour les PME françaises.
    Analysez la situation de l'entreprise suivante en vous basant sur les données fournies et l'axe d'analyse choisi.
    Soyez concret, réaliste et structurez votre réponse IMPERATIVEMENT en JSON valide comme demandé à la fin.

    **Données Internes de l'Entreprise :**
    {internal_data_str}

    **Données Externes Contextuelles (France - Estimations/Placeholders) :**
    - Taux d'inflation annuel récent estimé: {external_data.get('inflation_rate', '2.5')} %
    - Taux de croissance annuel récent estimé du secteur ({external_data.get('sector_code', 'N/A')}): {external_data.get('sector_growth_rate', '3.0')} %
    (Note: Ces données externes sont des placeholders, utilisez des hypothèses générales prudentes.)

    **Objectif Principal de l'Analyse (Axe choisi) :**
    {user_request_type_display}

    {guided_responses_str}
    """
    # Ajouter la description libre seulement si elle existe ET si l'axe est 'Autre' OU s'il n'y avait pas de réponses guidées
    if user_description and (scenario_request.request_type == 'other' or not scenario_request.guided_responses.exists()):
         prompt += f"**Description Libre Fournie par l'Utilisateur :**\n{user_description}\n\n"
    elif user_description: # Si description fournie en plus des réponses guidées
         prompt += f"**Commentaire Additionnel de l'Utilisateur :**\n{user_description}\n\n"


    prompt += """
    **Instructions pour la Réponse :**
    1.  **Synthèse Rapide :** Brève synthèse (2-3 phrases) de la situation actuelle perçue et de l'objectif.
    2.  **Analyse Prospective (3 ans) :** Projection (CA, Charges Totales, Marge Brute Annuelle) pour N+1, N+2, N+3. BASEZ les hypothèses sur les données internes, externes ET LES RÉPONSES SPÉCIFIQUES fournies ci-dessus. Expliquez les hypothèses clés utilisées.
    3.  **Risques Majeurs (Top 2-3) :** Identifiez 2 ou 3 risques principaux EN LIEN AVEC L'AXE D'ANALYSE et les réponses fournies.
    4.  **Recommandations Clés (Top 2-3) :** Proposez 2 ou 3 actions concrètes en réponse directe à l'axe d'analyse et aux réponses fournies. Codez chaque recommandation ([VERT] pour fort potentiel/conseillé, [ORANGE] pour potentiel modéré/prudence, [ROUGE] pour déconseillé/risque élevé).
    5.  **Format de Sortie IMPERATIF (JSON Valide Strict) :**
        {{
          "synthese": "Votre synthèse concise ici...",
          "previsions_3_ans": [
            {{"annee": "N+1", "ca_prev": VALEUR_NUMERIQUE, "charges_prev": VALEUR_NUMERIQUE, "marge_brute_prev": VALEUR_NUMERIQUE}},
            {{"annee": "N+2", "ca_prev": VALEUR_NUMERIQUE, "charges_prev": VALEUR_NUMERIQUE, "marge_brute_prev": VALEUR_NUMERIQUE}},
            {{"annee": "N+3", "ca_prev": VALEUR_NUMERIQUE, "charges_prev": VALEUR_NUMERIQUE, "marge_brute_prev": VALEUR_NUMERIQUE}}
          ],
          "hypotheses_previsions": "Explication concise des hypothèses clés utilisées pour les prévisions (ex: croissance CA de X% basée sur..., charges variables indexées sur inflation Y%...)",
          "risques_cles": [
            "Description concise du risque clé 1...",
            "Description concise du risque clé 2...",
            "Description concise du risque clé 3..."
          ],
          "recommandations": [
            {{"recommendation": "Description concise de la recommandation 1...", "niveau": "[VERT]"}},
            {{"recommendation": "Description concise de la recommandation 2...", "niveau": "[ORANGE]"}},
            {{"recommendation": "Description concise de la recommandation 3...", "niveau": "[ROUGE]"}}
          ]
        }}
    Assurez-vous que la sortie est UNIQUEMENT ce JSON valide. Pas de texte avant, après, ni d'explications hors JSON. Utilisez des nombres pour les valeurs, pas de devise ou de texte comme 'Non disponible' (utilisez 0 ou null si une valeur est inconnue/non calculable).
    """
    return prompt

def call_openai_api(prompt):
    """Appelle l'API OpenAI et retourne la réponse brute."""
    if client is None:
        logger.error("Client OpenAI non initialisé. Vérifiez la clé API dans les settings.")
        return None
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Modèle puissant recommandé pour JSON structuré et analyse
            messages=[
                {"role": "system", "content": "Vous êtes un expert en analyse financière et stratégique pour PME françaises. Vous répondez exclusivement en format JSON valide en suivant la structure demandée."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }, # Très important pour forcer le JSON
            temperature=0.3, # Plus faible pour moins d'hallucination et plus de cohérence
            max_tokens=2500 # Augmenter un peu au cas où
        )
        ai_response = response.choices[0].message.content
        logger.info("Réponse reçue de l'API OpenAI.")
        # logger.debug(f"Réponse brute OpenAI: {ai_response}") # Décommenter pour debug fin
        return ai_response
    except AuthenticationError:
         logger.error("Erreur d'authentification OpenAI. Vérifiez la clé API.")
         return None
    except Exception as e:
        # Logguer l'erreur spécifique de l'API OpenAI si possible
        logger.error(f"Erreur API OpenAI lors de l'appel: {e} (Type: {type(e).__name__})")
        return None

def parse_ai_response(ai_response_str):
    """Tente de parser la réponse JSON de l'IA."""
    if not ai_response_str:
        logger.error("Tentative de parser une réponse IA vide.")
        return None
    try:
        parsed_json = json.loads(ai_response_str)
        # TODO: Ajouter une validation de schéma ici (Pydantic, jsonschema)
        # Exemple simple de vérification de clés principales:
        required_keys = ["synthese", "previsions_3_ans", "hypotheses_previsions", "risques_cles", "recommandations"]
        if not all(key in parsed_json for key in required_keys):
             logger.error(f"Réponse JSON de l'IA incomplète. Clés manquantes. Reçu: {parsed_json.keys()}")
             return None # Ou une structure d'erreur
        logger.info("Réponse JSON de l'IA parsée avec succès.")
        return parsed_json
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de parsing JSON réponse IA: {e}\nRéponse reçue:\n{ai_response_str}")
        return None


# --- Fonction d'Orchestration Principale ---
def perform_analysis(scenario_request_id):
    """Orchestre le processus d'analyse REELLE en utilisant les réponses guidées."""
    logger.info(f"Déclenchement de l'analyse REELLE pour demande {scenario_request_id}")
    scenario_request = None # Initialiser pour le bloc except
    try:
        scenario_request = get_object_or_404(ScenarioRequest, id=scenario_request_id)
        # Vérifier si déjà complété ou échoué pour éviter de relancer
        if scenario_request.status in ['completed', 'failed', 'processing']:
             logger.warning(f"Tentative de relancer l'analyse pour SR {scenario_request_id} avec statut {scenario_request.status}. Annulation.")
             # On ne retourne pas False ici, car ce n'est pas une erreur d'exécution
             return True # Indique que l'opération est "terminée" (ou déjà en cours)

        company_profile = scenario_request.company_profile
        scenario_request.status = 'processing'
        scenario_request.save(update_fields=['status']) # Mettre à jour seulement le statut

        # 1. Récupérer Données Externes (Utilisation de placeholders)
        logger.info(f"Utilisation de données externes placeholders pour SR {scenario_request_id}.")
        external_data = {
            'inflation_rate': 2.5, # Placeholder
            'sector_growth_rate': 3.0, # Placeholder
            'sector_code': company_profile.sector_code
        }
        # Remplacer par les appels réels quand prêts:
        # insee_token = get_insee_access_token()
        # inflation = fetch_latest_inflation_rate(insee_token) if insee_token else None
        # growth = fetch_sector_growth_rate(insee_token, company_profile.sector_code) if insee_token else None
        # external_data = {'inflation_rate': inflation, 'sector_growth_rate': growth, 'sector_code': company_profile.sector_code}
        logger.info(f"Données externes (placeholders): {external_data}")

        # 2. Formater Données Internes
        internal_data_str = format_internal_data(company_profile)

        # 3. Préparer le Prompt
        prompt = prepare_openai_prompt(internal_data_str, external_data, scenario_request)

        # 4. Appeler OpenAI API
        logger.info(f"Appel API OpenAI pour demande {scenario_request_id}")
        ai_response_str = call_openai_api(prompt)

        # 5. Parser et Sauvegarder
        if not ai_response_str: raise Exception("Aucune réponse reçue de l'API OpenAI.")

        logger.info(f"Réponse OpenAI reçue pour {scenario_request_id}. Parsing...")
        parsed_result = parse_ai_response(ai_response_str)

        if not parsed_result: raise Exception("Erreur lors du parsing de la réponse JSON de l'IA.")

        ScenarioResult.objects.update_or_create(
            request=scenario_request,
            defaults={'generated_data': parsed_result}
        )
        scenario_request.status = 'completed'
        scenario_request.save(update_fields=['status']) # Mettre à jour seulement statut
        logger.info(f"Analyse REELLE terminée avec succès pour {scenario_request_id}")
        return True

    except Exception as e:
        logger.error(f"Échec analyse REELLE pour demande {scenario_request_id}: {e}")
        if scenario_request: # Vérifier si scenario_request a été chargé
            try:
                scenario_request.status = 'failed'
                scenario_request.save(update_fields=['status'])
            except Exception as e2:
                 logger.error(f"Impossible de mettre le statut à failed pour {scenario_request_id}: {e2}")
        return False

# --- Données Fictives pour Simulation ---

MOCK_ANALYSIS_RESULT_JSON = {
  "synthese": "Simulation: L'entreprise montre une croissance stable du CA mais des charges variables élevées. Le nouveau projet semble prometteur mais nécessite une gestion prudente des coûts.",
  "previsions_3_ans": [
    {"annee": "N+1", "ca_prev": 115000.00, "charges_prev": 80000.00, "marge_brute_prev": 35000.00},
    {"annee": "N+2", "ca_prev": 130000.00, "charges_prev": 88000.00, "marge_brute_prev": 42000.00},
    {"annee": "N+3", "ca_prev": 145000.00, "charges_prev": 95000.00, "marge_brute_prev": 50000.00}
  ],
  "hypotheses_previsions": "Simulation: Croissance CA simulée à +15% N+1, +13% N+2, +11.5% N+3. Charges augmentent de 10% N+1 puis 8% par an.",
  "risques_cles": [
    "Simulation: Dépendance forte au produit principal.",
    "Simulation: Augmentation imprévue du coût des matières premières.",
    "Simulation: Arrivée d'un nouveau concurrent local."
  ],
  "recommandations": [
    {"recommendation": "Simulation: Diversifier l'offre de produits/services pour réduire la dépendance.", "niveau": "[VERT]"},
    {"recommendation": "Simulation: Renégocier les contrats fournisseurs ou chercher des alternatives pour maîtriser les coûts variables.", "niveau": "[ORANGE]"},
    {"recommendation": "Simulation: Lancer une campagne marketing ciblée pour renforcer la notoriété face à la concurrence.", "niveau": "[VERT]"}
  ]
}

# --- Fonction de Simulation ---

def create_mock_analysis(scenario_request_id):
    """Simule une analyse réussie en créant un résultat avec des données fictives."""
    logger.info(f"Début SIMULATION analyse pour demande {scenario_request_id}")
    try:
        scenario_request = get_object_or_404(ScenarioRequest, id=scenario_request_id)
        # Mettre à jour statut
        scenario_request.status = 'processing'
        scenario_request.save()

        # Simuler un délai de traitement
        time.sleep(2) # Attend 2 secondes

        # Créer ou mettre à jour ScenarioResult avec les données MOCK
        ScenarioResult.objects.update_or_create(
            request=scenario_request,
            defaults={'generated_data': MOCK_ANALYSIS_RESULT_JSON} # Utilise le JSON fictif
        )

        # Mettre à jour le statut final
        scenario_request.status = 'completed'
        scenario_request.save()
        logger.info(f"SIMULATION analyse terminée avec succès pour demande {scenario_request_id}")
        return True

    except Exception as e:
        logger.error(f"Échec de la SIMULATION d'analyse pour demande {scenario_request_id}: {e}")
        try:
            scenario_request = ScenarioRequest.objects.get(id=scenario_request_id)
            scenario_request.status = 'failed'
            scenario_request.save()
        except ScenarioRequest.DoesNotExist:
            pass
        return False

