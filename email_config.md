# Configuration Email pour Benedicte.io

Ce document explique comment configurer l'envoi d'emails depuis l'application Django Benedicte.io, notamment pour l'email de finalisation d'inscription (définition du mot de passe).

## Modes de Configuration

Django propose plusieurs backends pour l'envoi d'emails :

1.  **Console Backend (Développement):** N'envoie pas de vrais emails, mais affiche leur contenu dans la console où `runserver` est lancé. Idéal pour le développement local rapide.
2.  **SMTP Backend (Production/Test Réel):** Utilise un serveur SMTP externe (comme Mailtrap, SendGrid, Mailgun, Gmail SMTP, etc.) pour envoyer de vrais emails ou les capturer pour inspection.

## 1. Configuration Console (Développement Local)

C'est la configuration par défaut si `DEBUG=True` dans le `settings.py` actuel.

*   **`settings.py` :**
    ```python
    if DEBUG:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    # ...
    DEFAULT_FROM_EMAIL = 'Benedicte.io Dev <noreply@example.com>' # Adresse d'expéditeur affichée
    ```
*   **Fonctionnement :** Quand l'application tente d'envoyer un email (ex: `send_set_password_email`), le contenu complet de l'email (en-têtes, corps texte, corps HTML) s'affiche dans le terminal où `python manage.py runserver` est exécuté.
*   **Avantage :** Simple, pas de configuration externe requise.
*   **Inconvénient :** Ne teste pas la délivrabilité réelle ni le rendu dans un client email.

## 2. Configuration Mailtrap (Test/Staging)

Mailtrap est un service qui **capture** les emails envoyés via SMTP sans les délivrer aux vrais destinataires. Parfait pour tester les emails générés par l'application dans un environnement de staging ou même en local si on veut voir le rendu HTML.

*   **Prérequis :** Un compte Mailtrap gratuit ([https://mailtrap.io/](https://mailtrap.io/)).
*   **Configuration Mailtrap :**
    1.  Connectez-vous à Mailtrap.
    2.  Allez dans "Email Testing" > "Inboxes".
    3.  Cliquez sur votre Inbox (ex: "Demo inbox").
    4.  Allez dans l'onglet "SMTP Settings".
    5.  Notez les identifiants fournis : **Host**, **Port** (ex: 587 ou 2525), **Username**, **Password**.
*   **Configuration Django (`.env`) :**
    ```dotenv
    # .env - Configuration pour Mailtrap (Test/Staging)
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST='sandbox.smtp.mailtrap.io' # Ou l'host fourni
    EMAIL_PORT=2525 # Ou le port fourni (vérifier TLS/SSL)
    EMAIL_USE_TLS=True # Généralement True pour les ports 587, 2525
    EMAIL_USE_SSL=False
    EMAIL_HOST_USER='VOTRE_USERNAME_MAILTRAP'
    EMAIL_HOST_PASSWORD='VOTRE_PASSWORD_MAILTRAP'
    DEFAULT_FROM_EMAIL='Benedicte.io Test <test@votre-domaine-fictif.com>'
    ```
*   **Configuration Django (`settings.py`) :** Assurez-vous que ces variables sont lues depuis `.env` lorsque `DEBUG=False` (ou forcez ce backend si vous voulez tester avec Mailtrap en mode DEBUG).
*   **Fonctionnement :** Les emails envoyés par Django seront interceptés par Mailtrap et visibles dans votre Inbox Mailtrap sur leur site web.
*   **Avantage :** Permet de voir le rendu HTML/Texte exact, de vérifier les liens sans envoyer de spam.
*   **Inconvénient :** Nécessite un compte Mailtrap et la configuration des variables.

## 3. Configuration SendGrid (Production - Exemple)

SendGrid est un service d'envoi d'emails transactionnels robuste, adapté à la production. Il propose un plan gratuit.

*   **Prérequis :**
    *   Un compte SendGrid ([https://sendgrid.com/](https://sendgrid.com/)).
    *   Une **Identité d'Expéditeur Vérifiée** (Single Sender Verification ou Domain Authentication).
    *   Une **Clé API SendGrid** avec les permissions d'envoi d'emails ("Mail Send").
*   **Configuration Django (`.env`) :**
    ```dotenv
    # .env - Configuration pour SendGrid (Production)
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST='smtp.sendgrid.net'
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER='apikey' # Obligatoirement 'apikey' pour SendGrid
    EMAIL_HOST_PASSWORD='SG.xxxxxxxxxxxxxxxxxxxxxxx' # VOTRE CLE API SENDGRID
    DEFAULT_FROM_EMAIL='Benedicte.io <votre_email_verifie@domaine.com>' # Email vérifié sur SendGrid
    ```
*   **Configuration Django (`settings.py`) :** Assurez-vous que ces variables sont lues depuis `.env` lorsque `DEBUG=False`.
*   **Fonctionnement :** Les emails seront réellement envoyés via les serveurs de SendGrid au destinataire final.
*   **Avantage :** Envoi réel, suivi des envois possible via SendGrid.
*   **Inconvénient :** Nécessite configuration SendGrid complète, attention à ne pas spammer pendant les tests.

**Vérification :**

*   Après configuration (Console, Mailtrap ou SendGrid), déclenchez un envoi d'email via l'application (ex: inscription Stripe test).
*   Vérifiez la sortie (console, inbox Mailtrap, ou boîte de réception réelle) pour confirmer que l'email est généré/envoyé correctement.
*   Cliquez sur les liens dans l'email (comme celui de définition de mot de passe) pour vérifier qu'ils fonctionnent.