# Configuration OpenAI (GPT) pour Benedicte.io

Ce document explique comment obtenir et configurer la clé API OpenAI nécessaire au fonctionnement du moteur d'analyse IA de Benedicte.io.

**Prérequis :**

*   Un compte OpenAI ([https://platform.openai.com/signup](https://platform.openai.com/signup)). Notez que l'utilisation de l'API GPT-4 ou d'autres modèles avancés peut nécessiter la configuration d'un moyen de paiement sur votre compte OpenAI.

## Étapes de Configuration OpenAI

1.  **Accéder aux Clés API :**
    *   Connectez-vous à la plateforme OpenAI : [https://platform.openai.com/](https://platform.openai.com/)
    *   Cliquez sur votre profil/icône en haut à droite, puis sur "View API keys" (ou naviguez vers la section API Keys dans le menu de gauche).

2.  **Créer une Nouvelle Clé Secrète :**
    *   Cliquez sur le bouton "**+ Create new secret key**".
    *   Donnez un nom descriptif à votre clé (ex: `Benedicte.io Django App`).
    *   Cliquez sur "**Create secret key**".

3.  **Copier et Stocker la Clé :**
    *   **TRÈS IMPORTANT :** OpenAI n'affichera la clé secrète complète **qu'une seule fois**, juste après sa création.
    *   **Copiez immédiatement** la clé (elle commence généralement par `sk-...`).
    *   **Stockez-la en lieu sûr** (comme un gestionnaire de mots de passe). Ne la perdez pas et ne la partagez pas publiquement. Si vous la perdez, vous devrez en générer une nouvelle.

## Configuration Django (`.env`)

Ajoutez la clé API récupérée à votre fichier `.env` (ou aux variables d'environnement de votre serveur) :

```dotenv
# .env - Clé API OpenAI

OPENAI_API_KEY='sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' # Collez votre clé secrète ici
```

**Vérification :**

1.  **`settings.py` :** Assurez-vous que `settings.py` lit bien cette variable :
    ```python
    OPENAI_API_KEY = env('OPENAI_API_KEY', default=None)
    ```
2.  **`analysis/services.py` :** Le code dans ce fichier utilise `settings.OPENAI_API_KEY` pour initialiser le client OpenAI.
3.  **Test Fonctionnel :**
    *   Mettez la variable d'environnement `USE_MOCK_ANALYSIS` à `False` dans votre `.env` (ou dans les settings Render).
    *   Redémarrez votre serveur Django.
    *   Lancez une analyse via l'application.
    *   **Surveillez les logs Django :**
        *   Vous devriez voir des messages indiquant "Déclenchement de l'analyse REELLE...".
        *   Vous devriez voir "Appel API OpenAI...".
        *   Vérifiez s'il y a des erreurs (`Erreur API OpenAI`, `Erreur d'authentification OpenAI`). Une erreur d'authentification indique souvent une clé API incorrecte ou invalide.
        *   Si l'appel réussit, vous devriez voir "Réponse OpenAI reçue..." et "Analyse REELLE terminée succès...".
    *   **Vérifiez le résultat** sur le tableau de bord. L'analyse doit être différente du mock et potentiellement plus pertinente (bien que sa qualité dépende fortement du prompt et des données fournies).

**Modèle Utilisé :**

Actuellement, le service `analysis/services.py` est configuré pour utiliser le modèle `"gpt-4o"` (modifiable dans la fonction `call_openai_api`). Ce choix peut impacter les coûts et la qualité des réponses.

**Coûts :**

L'utilisation de l'API OpenAI est **payante** basée sur le nombre de tokens (morceaux de mots) utilisés en entrée (prompt) et en sortie (réponse). Surveillez votre consommation sur le dashboard OpenAI.

**Passage en Production :**

*   La même clé API peut généralement être utilisée pour le développement et la production.
*   Assurez-vous que la variable d'environnement `OPENAI_API_KEY` est bien définie sur votre serveur de production (Render).
*   Surveillez les coûts et définissez éventuellement des limites de budget sur votre compte OpenAI.