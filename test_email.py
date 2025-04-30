import smtplib
from email.message import EmailMessage
import ssl
import socket # Pour attraper les erreurs de connexion réseau/DNS

# --- Configuration SMTP (basée sur vos données) ---
EMAIL_HOST = "mail70.lwspanel.com"
EMAIL_PORT = 465  # Port 465 utilise généralement SMTP_SSL (connexion sécurisée dès le départ)
# EMAIL_USE_TLS = True # Ceci est implicite avec SMTP_SSL sur le port 465.
                      # Si le port était 587, on utiliserait smtplib.SMTP() puis server.starttls()
EMAIL_HOST_USER = "contact@benedicte.io"
EMAIL_HOST_PASSWORD = "kA7!J53@N7!F_rF" # ATTENTION: Stocker le mot de passe en clair dans un script est risqué
DEFAULT_FROM_EMAIL = "contact@benedicte.io"

#williamkpessouaklamavo@gmail.com

# --- Destinataire pour le test ---
# Demande à l'utilisateur où envoyer l'email de test
recipient_email = input("Entrez l'adresse email du DESTINATAIRE pour le test : ")
if not recipient_email:
    print("L'adresse email du destinataire est requise. Arrêt.")
    exit()

# --- Création du message ---
subject = "Email de Test SMTP depuis Python"
body = f"""Bonjour,

Ceci est un email de test automatique envoyé via un script Python
pour vérifier la configuration SMTP suivante :

HOST: {EMAIL_HOST}
PORT: {EMAIL_PORT} (Utilisation de SMTP_SSL car port 465)
USER: {EMAIL_HOST_USER}

Si vous recevez cet email, la configuration semble fonctionner.

Cordialement,
Votre Script de Test
"""

msg = EmailMessage()
msg['Subject'] = subject
msg['From'] = DEFAULT_FROM_EMAIL
msg['To'] = recipient_email
msg.set_content(body)

# --- Connexion et envoi ---
server = None # Initialisation pour le bloc finally
print("\n--- Début du Test d'Envoi d'Email ---")
try:
    # Le port 465 implique une connexion SSL dès le début (SMTP_SSL)
    print(f"1. Tentative de connexion à {EMAIL_HOST}:{EMAIL_PORT} via SMTP_SSL...")
    # Création d'un contexte SSL par défaut pour une meilleure compatibilité
    context = ssl.create_default_context()
    server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context)
    print("   Connexion SSL établie avec succès.")

    # Optionnel: Activer le mode debug pour voir les échanges SMTP détaillés
    # server.set_debuglevel(1)

    print(f"2. Tentative d'authentification en tant que {EMAIL_HOST_USER}...")
    server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    print("   Authentification réussie.")

    print(f"3. Envoi de l'email à {recipient_email}...")
    server.send_message(msg)
    print(f"   Email envoyé avec succès à {recipient_email} !")
    print("\n--- TEST RÉUSSI ---")

except smtplib.SMTPAuthenticationError as e:
    print("\n--- ERREUR D'AUTHENTIFICATION ---")
    print(f"   Échec de l'authentification (Code: {e.smtp_code}): {e.smtp_error}")
    print("   Vérifiez que EMAIL_HOST_USER et EMAIL_HOST_PASSWORD sont corrects.")
    print("   Assurez-vous que l'authentification SMTP est activée sur le serveur pour ce compte.")
except smtplib.SMTPConnectError as e:
    print("\n--- ERREUR DE CONNEXION ---")
    print(f"   Impossible de se connecter au serveur {EMAIL_HOST} sur le port {EMAIL_PORT}.")
    print(f"   Détails: {e}")
    print("   Vérifiez que l'adresse du serveur (EMAIL_HOST) et le port (EMAIL_PORT) sont corrects.")
    print("   Vérifiez votre connexion réseau et si un pare-feu bloque la connexion sur ce port.")
except smtplib.SMTPServerDisconnected:
     print("\n--- ERREUR ---")
     print("   Le serveur s'est déconnecté de manière inattendue. Réessayez ou vérifiez l'état du serveur.")
except ssl.SSLError as e:
     print("\n--- ERREUR SSL/TLS ---")
     print(f"   Une erreur SSL s'est produite lors de la connexion: {e}")
     print("   Cela peut être dû à un problème de certificat sur le serveur ou à une incompatibilité de protocole.")
     print(f"   Vérifiez la configuration SSL/TLS du serveur ({EMAIL_HOST}).")
except socket.gaierror as e:
     print("\n--- ERREUR RÉSEAU/DNS ---")
     print(f"   Impossible de résoudre le nom d'hôte '{EMAIL_HOST}'.")
     print(f"   Détails: {e}")
     print("   Vérifiez l'orthographe de EMAIL_HOST et votre configuration DNS.")
except Exception as e:
    print("\n--- ERREUR INATTENDUE ---")
    print(f"   Une erreur s'est produite lors de l'envoi de l'email: {type(e).__name__} - {e}")
finally:
    # Assurez-vous de fermer la connexion même en cas d'erreur
    if server:
        print("4. Fermeture de la connexion SMTP...")
        try:
            server.quit()
            print("   Connexion fermée.")
        except Exception as e:
            print(f"   Erreur lors de la fermeture de la connexion: {e}")

print("--- Fin du Script ---")