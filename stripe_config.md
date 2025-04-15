# Configuration Stripe pour Benedicte.io

Ce document détaille les étapes nécessaires pour configurer Stripe afin qu'il fonctionne avec l'application SaaS Benedicte.io, notamment pour la gestion de l'abonnement mensuel obligatoire à l'inscription.

**Prérequis :**

*   Un compte Stripe ([https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)).

**Modes Stripe :**

Stripe fonctionne en deux modes : **Test** et **Production (Live)**.

*   **Mode Test :** Utilisez ce mode pour tout le développement et les tests. Il utilise des clés API de test et des numéros de carte de crédit fictifs. Aucune transaction réelle n'est effectuée.
*   **Mode Production (Live) :** Utilisez ce mode lorsque l'application est prête à accepter de vrais paiements. Il utilise des clés API Live et traite de vraies transactions.

**IMPORTANT :** Effectuez toutes les étapes suivantes d'abord en **Mode Test**. Vous devrez les répéter en Mode Production avant le lancement final.

## Étapes de Configuration Stripe

1.  **Créer le Produit d'Abonnement :**
    *   Connectez-vous à votre Dashboard Stripe (en Mode Test).
    *   Naviguez vers "Produits" dans le menu de gauche.
    *   Cliquez sur "+ Ajouter un produit".
    *   **Nom :** `Abonnement Mensuel Benedicte.io` (ou similaire)
    *   **Description (Optionnel) :** `Accès complet aux fonctionnalités d'analyse de Benedicte.io.`
    *   Faites défiler jusqu'à "Tarification".
    *   **Modèle tarifaire :** "Tarification standard".
    *   **Type de tarification :** Sélectionnez "**Récurrent**".
    *   **Montant :** Entrez `9.99`.
    *   **Devise :** Sélectionnez `EUR` (Euro).
    *   **Intervalle de facturation :** Sélectionnez "**Mensuel**".
    *   Cliquez sur "**Enregistrer le produit**".

2.  **Récupérer l'ID du Tarif (Price ID) :**
    *   Sur la page du produit que vous venez de créer, dans la section "Tarification", localisez le prix de 9,99 € / mois.
    *   Cliquez dessus ou cherchez une option pour copier son ID.
    *   Copiez l'**ID de l'API** (il commence par `price_...`).
    *   **Notez cet ID.** Vous en aurez besoin pour la configuration Django.

3.  **Récupérer les Clés API :**
    *   Dans le Dashboard Stripe (toujours en Mode Test), allez dans "Développeurs" > "Clés API".
    *   Vous verrez :
        *   **Clé publiable (Publishable key) :** Elle commence par `pk_test_...`. Copiez-la.
        *   **Clé secrète (Secret key) :** Cliquez sur "Révéler la clé de test". Elle commence par `sk_test_...`. Copiez-la **immédiatement et stockez-la en sécurité**, elle ne sera plus affichée.
    *   **Notez ces deux clés.**

4.  **Configurer le Point de Terminaison Webhook :**
    *   Allez dans "Développeurs" > "Webhooks".
    *   Cliquez sur "+ Ajouter un point de terminaison".
    *   **URL du point de terminaison :**
        *   *Pour le développement local avec `stripe listen` :* Vous n'avez pas besoin de le créer ici, `stripe listen` vous donnera un secret temporaire.
        *   *Pour le déploiement sur Render (ou autre) :* Entrez l'URL publique complète de votre vue webhook. Exemple pour Render : `https://VOTRE-APP-NAME.onrender.com/stripe-webhook/` (remplacez `VOTRE-APP-NAME`).
    *   **Description (Optionnel) :** `Webhook Benedicte.io (Test)`
    *   **Événements à écouter :** Cliquez sur "+ Sélectionner les événements". Recherchez et sélectionnez :
        *   `checkout.session.completed` (essentiel pour créer l'utilisateur après paiement).
        *   *Optionnel mais recommandé pour gérer le cycle de vie :* `customer.subscription.deleted`, `customer.subscription.updated`, `invoice.payment_failed`.
    *   Cliquez sur "Ajouter les événements".
    *   Cliquez sur "Ajouter le point de terminaison".
    *   **Récupérer le Secret de Signature :** Sur la page du webhook que vous venez de créer, cliquez sur "**Révéler**" à côté de "**Secret de signature**" (Signing secret). Copiez cette clé (elle commence par `whsec_...`).
    *   **Notez ce secret.**

5.  **Configurer le Portail Client (Basique) :**
    *   Allez dans "Paramètres" (icône roue dentée).
    *   Dans la section "Billing" (Facturation), cliquez sur "Portail client".
    *   Vérifiez que les fonctionnalités de base sont activées (ex: mettre à jour le moyen de paiement, voir l'historique des factures).
    *   Cliquez sur "**Enregistrer**" (même si vous n'avez rien changé). Cela crée la configuration par défaut nécessaire pour l'API en mode test.

## Configuration Django (`.env`)

Ajoutez les clés et ID récupérés à votre fichier `.env` (ou aux variables d'environnement de votre serveur) :

```dotenv
# .env - Clés de TEST Stripe

STRIPE_PUBLISHABLE_KEY='pk_test_xxxxxxxxxxxxxx'
STRIPE_SECRET_KEY='sk_test_xxxxxxxxxxxxxx'
STRIPE_PRICE_ID='price_xxxxxxxxxxxxxx' # L'ID du tarif 9.99€/mois
STRIPE_WEBHOOK_SECRET='whsec_xxxxxxxxxxxxxx' # Le secret du webhook pointant vers votre app
```

**Vérification :**

*   Assurez-vous que `settings.py` lit bien ces variables.
*   Testez le flux d'inscription complet en Mode Test Stripe.
*   Vérifiez les logs de votre application et de `stripe listen` (si utilisé) pour confirmer la réception et la validation du webhook.
*   Vérifiez la création de l'utilisateur dans l'admin Django avec les ID Stripe associés.

**Passage en Production :**

*   Répétez les étapes 1 à 5 dans le **Mode Production (Live)** de Stripe.
*   Récupérez les **clés API Live** (`pk_live_...`, `sk_live_...`), l'**ID du Prix Live**, et le **Secret du Webhook Live**.
*   Mettez à jour les variables d'environnement de votre serveur de production (Render) avec ces **nouvelles clés Live**. **NE JAMAIS** commiter les clés Live dans votre code.