# 🌍 TravelPro - ERP de Gestion pour Agences de Voyage (Odoo 16)

**TravelPro** est une solution verticale complète développée sous Odoo 16, conçue spécifiquement pour répondre aux besoins opérationnels et financiers des agences de voyage modernes. Ce module transforme Odoo en un outil métier puissant capable de gérer l'intégralité du cycle de vie d'un dossier voyage.

---

## 📑 Table des Matières
1. [Fonctionnalités Principales](#-fonctionnalités-principales)
2. [Modules Détaillés](#-modules-détaillés)
3. [Gestion Financière & Comptable](#-gestion-financière--comptable)
4. [Documents & Rapports](#-documents--rapports)
5. [Installation](#-installation)
6. [Guide de Configuration](#-guide-de-configuration)
7. [Workflow Opérationnel](#-workflow-opérationnel)
8. [Structure Technique](#-structure-technique)

---

## 🚀 Fonctionnalités Principales

*   **Centralisation** : Gestion unique pour Hôtels, Vols, Transferts, Excursions, et Assurances.
*   **Workflow Métier** : Processus de validation rigoureux (Brouillon -> Confirmé -> Facturé -> Soldé).
*   **CRM Voyageurs** : Fiches clients enrichies (Préférences, Historique, Documents d'identité).
*   **Facturation Avancée** : Calcul TVA sur marge ou totale, Timbre fiscal, Gestion multi-devises.
*   **Trésorerie** : Caisse physique, reçus automatiques, suivi des acomptes.

---

## 📦 Modules Détaillés

### 1️⃣ Gestion des Réservations (`travel.reservation`)
Le cœur du système. Chaque dossier de réservation centralise toutes les informations :
*   **Détails du Voyage** : Destination, Dates (Check-in/out), Durée (Nuitées).
*   **Services Inclus** :
    *   *Hébergement* : Choix de l'hôtel, Type de chambre, Pension.
    *   *Vols* : Compagnie, Numéro de vol, Horaires.
    *   *Extras* : Transferts, Visites guidées.
*   **Participants (Pax)** : Liste détaillée des adultes, enfants et bébés avec liaison automatique vers les fiches contacts.

### 2️⃣ Gestion des Clients & Passagers
*   **Fiches Membres** : Extension des contacts Odoo pour gérer les spécificités "Voyageur".
*   **Documents** : Suivi des dates d'expiration (Passeports, Visas).
*   **Relationnel** : Historique complet des voyages et des paiements par client.

### 3️⃣ Gestion des Fournisseurs (`res.partner`)
*   **Refactorisation** : Intégration complète dans le modèle standard Odoo.
*   **Fiscalité** : Configuration du taux de TVA par défaut et de la Retenue à la Source directement sur la fiche fournisseur.
*   **Achats** : Génération de Bons de Commande liés aux réservations pour le suivi des coûts (Yied Management).

---

## 💰 Gestion Financière & Comptable

### 🧾 Facturation Client
Un moteur de facturation adapté aux normes locales (Tunisie / International) :
*   **Calcul Inversé** : Saisie du prix TTC -> Le système calcule automatiquement le HT et la TVA selon le taux configuré.
*   **Timbre Fiscal** : Ajout automatique du timbre fiscal (ex: 1.000 TND) sur les factures, configurable dans les paramètres.
*   **Mentions Légales** : Affichage automatique des bases taxables et non taxables.

### 💵 Caisse & Encaissements (`cash.register`)
*   **Interface Caisse** : Module simplifié pour les agents de comptoir.
*   **Opérations** : Saisie rapide des Recettes (Paiements clients) et Dépenses (Menus frais).
*   **Contrôle** : Ouverture et Fermeture de caisse avec vérification des soldes théoriques vs réels.

---

## 📄 Documents & Rapports

Tous les documents sont générés au format PDF professionnel avec QWeb :

1.  **Devis de Voyage** :
    *   Présentation commerciale de l'offre.
    *   Détails des prestations et prix total.
    *   Validité de l'offre.
2.  **Facture Client** :
    *   Format A4 réglementaire.
    *   Colonnes détaillées : Qté, Prix Unitaire, Remise, HT, TVA, TTC.
    *   Totaux clairs avec distinction du Timbre Fiscal.
    *   **Montant en toutes lettres** automatique.
3.  **Reçu de Caisse** :
    *   Format compact (A5/Ticket) pour impression thermique ou standard.
    *   Design optimisé : Logo agence, Informations légales, Référence réservation.
    *   Signature Client / Caissier.

---

## 🛠 Installation

### Pré-requis Techniques
*   **Serveur** : Odoo 16 (Community ou Enterprise).
*   **Python** : Version 3.8 ou supérieure.
*   **Dépendances Python** :
    ```bash
    pip install num2words
    ```
    *(Nécessaire pour la conversion des montants en lettres sur les factures)*

### Procédure
1.  Placer le dossier `travel_pro_version1` dans votre répertoire `addons` Odoo.
2.  Redémarrer le service Odoo.
3.  Activer le "Mode Développeur" dans Odoo.
4.  Aller dans **Applications** -> **Mettre à jour la liste des applications**.
5.  Rechercher **TravelPro** et cliquer sur **Activer**.

---

## ⚙️ Guide de Configuration

### 1. Configuration Société
*   Aller dans **Paramètres** -> **Sociétés**.
*   Renseigner Logo, Adresse, Matricule Fiscal, Téléphone. Ces infos apparaîtront sur tous les PDF.

### 2. Timbre Fiscal
*   Aller dans la configuration Comptabilité ou Produits.
*   Créer un produit de type "Service" nommé "Timbre Fiscal".
*   Configurer son prix (ex: 1.000).

### 3. Taxes
*   Vérifier les taxes (TVA 7%, 13%, 19%, etc.) dans le module Comptabilité.
*   Associer les comptes comptables corrects.

### 4. Séquences
*   Le module installe automatiquement les séquences pour les Réservations (`RES/202X/00001`) et Reçus (`REC/202X/...`). Elles sont modifiables dans **Paramètres Technique**.

---

## 🔄 Workflow Opérationnel

### Scénario Type : Vente d'un Séjour

1.  **Création du Dossier** :
    *   L'agent crée une **Réservation** (Status: *Brouillon*).
    *   Il saisit le Client, l'Hôtel, les Dates et le Prix TTC convenu.
2.  **Devis** :
    *   Clic sur **"Imprimer Devis"** pour remettre une offre au client.
3.  **Confirmation** :
    *   Le client accepte. L'agent clique sur **"Confirmer"**.
    *   Le statut passe à *Confirmé*.
4.  **Paiement (Acompte)** :
    *   L'agent va dans **Caisse** -> **Nouvelle Opération**.
    *   Il sélectionne la réservation, saisit le montant reçu.
    *   Il valide et le système imprime automatiquement le **Reçu de Caisse**.
5.  **Facturation** :
    *   Depuis la réservation, clic sur **"Facturer"**.
    *   Odoo génère la facture brouillon avec les bons comptes.
    *   Validation de la facture -> Impression PDF.
6.  **Clôture** :
    *   Une fois le voyage terminé et soldé, le dossier est marqué comme *Terminé*.

---

## 🏗 Structure Technique

```text
travel_pro_version1/
├── __manifest__.py          # Déclaration du module et dépendances
├── models/
│   ├── reservation.py       # Main Model: travel.reservation
│   ├── invoice_client.py    # Overrides: account.move (Calculs TVA/Timbre)
│   ├── partner.py           # Overrides: res.partner (TVA/Retenue fournisseur)
│   ├── cash_register.py     # Main Model: cash.register & operations
│   └── ...
├── views/
│   ├── menu.xml             # Structure du menu Travel Pro
│   ├── reservation_views.xml
│   ├── cash_register_views.xml
│   ├── report_invoice.xml   # Template QWeb Facture
│   ├── report_quote.xml     # Template QWeb Devis
│   ├── report_receipt.xml   # Template QWeb Reçu
│   └── ...
├── static/
│   └── img/                 # Assets graphiques
└── security/
    └── ir.model.access.csv  # Règles d'accès (ACL)
```

---
**Développé avec ❤️ pour l'industrie du voyage.**
*Copyright © 2025 TravelPro Solutions*
