URBAN.JEWELRYYY — Installation Android / Termux
================================================

Projet de boutique accessoires : Python + Flask (serveur), HTML/Jinja + CSS + JavaScript (interface), SQLite (commandes).
Le catalogue est vide au démarrage : vous ajoutez vos produits, prix et photos depuis l'espace Admin.

1) Installer Termux récent puis exécuter :

pkg update && pkg upgrade -y
pkg install python unzip -y
termux-setup-storage

2) Décompresser le ZIP dans le dossier Téléchargements, puis :

cd ~/storage/downloads
unzip Urban_jewelryyy_HTML_Termux.zip
cd urban_jewelryyy
pip install -r requirements.txt

3) Définir le mot de passe Admin et la clé de session :

export ADMIN_PASSWORD='VotreMotDePasseFortIci'
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python app.py

Ouvrir Chrome sur : http://127.0.0.1:5000
Espace Admin : http://127.0.0.1:5000/admin/login
Arrêter le serveur : CTRL + C

FONCTIONS
- Site en français avec bascule vers l'arabe (FR / عربي).
- Catalogue initialement vide.
- Ajout de produits depuis le téléphone, prix en DA, jusqu'à 8 photos par produit.
- Galerie photos avec aperçu plein écran.
- Formulaire client : nom, téléphone, wilaya, commune, quantité, domicile ou bureau.
- Les 58 wilayas et leurs communes sont chargées depuis un jeu de données public bilingue ; une connexion Internet est nécessaire pour charger la liste.
- Calcul du sous-total produits + livraison = total à payer.
- Tarifs de livraison recopiés depuis le tableau DHD fourni. Les wilayas 50, 54 et 56 n'ont pas de tarif sur l'image : vous pouvez les compléter depuis Admin > Tarifs de livraison. Le tarif est bloqué tant qu'il n'est pas renseigné.
- Les commandes sont enregistrées dans SQLite et visibles dans Admin, avec quantité, livraison et total final. Vous pouvez modifier le statut et supprimer une commande.
- Confirmation WhatsApp vers +213 550 329 112.

IMPORTANT
- Ne partagez jamais votre mot de passe Admin.
- Définissez ADMIN_PASSWORD et SECRET_KEY avant le démarrage, puis utilisez les mêmes valeurs après chaque redémarrage. Si ADMIN_PASSWORD n'est pas défini, le mot de passe local de test est UrbanSecure2026! ; remplacez-le obligatoirement avant publication.
- Le serveur Flask intégré convient aux tests locaux. Pour un site public, déployez avec Gunicorn/Render, HTTPS et un stockage persistant pour la base SQLite et les photos (les disques éphémères d'hébergement peuvent effacer les données après redémarrage).
- La création effective d'un envoi Yalidine/DHD via API n'est pas automatisée ; la commande est enregistrée et confirmée sur WhatsApp.

DONNÉES ADMINISTRATIVES
Liste 58 wilayas / 1 541 communes : Open Admin Data, CC-BY-4.0.
https://github.com/open-admin-data/algeria-administrative-divisions
