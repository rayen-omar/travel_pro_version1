# ✈️ TravelPro - Solution de Gestion pour Agences de Voyage (Odoo 16)

**TravelPro** est une solution verticale complète pour Odoo 16 dédiée aux agences de voyage. Elle centralise la gestion des réservations, de la facturation client/fournisseur, de la trésorerie et de la relation client.

---

## 📌 Fonctionnalités Clés

### 1️⃣ Gestion des Réservations
- **Workflow Complet** : De la demande initiale (Brouillon) à la confirmation (Confirmé) et clôture (Terminé).
- **Multi-Services** : Gestion unifiée des Hôtels, Vols, Transferts, Excursions et Assurances dans un dossier unique.
- **Documents & Devis** :
    - Génération de devis professionnels PDF ("Devis de Voyage") directement depuis la réservation.
    - Suivi des passagers (Pax) et détails du voyage.

### 2️⃣ Facturation Client Avancée
- **Calcul Automatisé** :
    - Calcul inversé des taxes : Saisie TTC -> Calcul automatique HT et TVA.
    - Gestion du **Timbre Fiscal** configurable.
    - Mentions légales conformes (Arrêté fiscal).
- **Rapports PDF Personnalisés** :
    - Mise en page professionnelle.
    - Logo de l'agence et coordonnées complètes.
    - Tableaux clairs avec colonnes : Prix Unitaire, Remise, HT, TVA, TTC.
    - Montant en toutes lettres (Chiffres et Lettres).

### 3️⃣ Gestion Fournisseurs & Achats
- **Centralisation** : Intégration de la logique "Facture Fournisseur" directement dans la fiche Contact (`res.partner`).
- **Fiscalité Fournisseur** :
    - Configuration du taux de TVA par défaut par fournisseur.
    - Gestion de la Retenue à la Source (taux configurable).
- **Achats de Services** : Création fluide de bons de commande fournisseurs liés aux dossiers de réservation.

### 4️⃣ Caisse & Trésorerie
- **Point de Vente Agence** : Interface simplifiée pour les encaissements comptoir.
- **Reçus de Paiement** :
    - Impression automatique des Reçus de Caisse.
    - **Format PDF Compact** (A5/A4 adaptable) optimisé pour l'impression économique.
    - Mentions obligatoires : Numéro de reçu, Caissier, Mode de paiement, Référence dossier.
    - Espace pour signature Client / Caissier.

### 5️⃣ CRM & Commissionnement
- Gestion de la base de données Clients (Voyageurs) et Entreprises.
- Suivi des commissions sur ventes.

---

## 🚀 Installation & Configuration

### Pré-requis
*   Odoo 16.0 Community ou Enterprise.
*   Modules dépendants : `sale`, `purchase`, `account`, `point_of_sale`.
*   Bibliothèque Python : `num2words` (pour les montants en lettres).

### Installation
1.  Cloner le dépôt dans votre dossier `addons` Odoo.
2.  Installer les dépendances Python : `pip install num2words`
3.  Mettre à jour la liste des applications dans Odoo.
4.  Installer le module **TravelPro**.

---

## 📂 Structure Technique

```
travel_pro_version1/
├── models/
│   ├── reservation.py        # Logique métier Réservations
│   ├── invoice_client.py     # Surcharge Facturation Client
│   ├── partner.py            # Extension Fiche Partenaire (Fournisseurs)
│   ├── cash_register.py      # Gestion Caisse & Opérations
│   └── ...
├── views/
│   ├── reservation_views.xml # Vues Réservation
│   ├── report_invoice.xml    # Template PDF Facture
│   ├── report_quote.xml      # Template PDF Devis
│   ├── report_receipt.xml    # Template PDF Reçu Caisse
│   └── ...
├── static/
│   └── img/                  # Logos et Assets
└── ...
```

---

## 📝 Dernières Mises à Jour (Changelog)

### Version Actuelle
*   **[NEW] Devis PDF** : Ajout du bouton "Imprimer Devis" et du rapport associé.
*   **[NEW] Reçu de Caisse** : Nouveau design compact, logo à gauche, police agrandie pour lisibilité.
*   **[FIX] Facturation** : Correction du calcul HT/TTC et affichage du Timbre Fiscal.
*   **[REFACTOR] Fournisseurs** : Suppression du modèle "Facture Fournisseur" séparé -> Intégration native dans Contacts.

---

## 📞 Support

Pour toute question ou assistance technique concernant ce module, veuillez contacter l'équipe de développement.

---
*Ce projet est maintenu par l'équipe de développement TravelPro.*
