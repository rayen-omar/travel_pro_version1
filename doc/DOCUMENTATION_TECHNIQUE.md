# 📚 Documentation Technique - TravelPro ERP

## Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Architecture du Module](#architecture-du-module)
3. [Modèles de Données](#modèles-de-données)
4. [Système de Sécurité](#système-de-sécurité)
5. [Flux Métier](#flux-métier)
6. [API et Intégrations](#api-et-intégrations)
7. [Tests](#tests)
8. [Installation et Configuration](#installation-et-configuration)
9. [Maintenance](#maintenance)

---

## 1. Vue d'Ensemble

### Description
TravelPro ERP est un module Odoo 16 complet pour la gestion d'agences de voyage. Il couvre l'ensemble du cycle de vie d'une réservation, de la création du client jusqu'au paiement et à la facturation.

### Informations Techniques
| Élément | Valeur |
|---------|--------|
| Version | 16.0.4.0 |
| Framework | Odoo 16 Community |
| Langage | Python 3.10+ |
| Base de données | PostgreSQL 13+ |
| Licence | OPL-1 (Propriétaire) |

### Dépendances
```python
'depends': [
    'base',      # Modèles de base Odoo
    'sale',      # Gestion des ventes
    'account',   # Comptabilité
    'purchase',  # Achats
    'point_of_sale',  # Point de vente
    'mail',      # Messages et activités
]
```

---

## 2. Architecture du Module

### Structure des Fichiers
```
travel_pro_version1/
├── __init__.py              # Point d'entrée du module
├── __manifest__.py          # Manifeste du module
├── models/                  # Modèles Python
│   ├── __init__.py
│   ├── mixins.py           # Mixins réutilisables
│   ├── company.py          # Sociétés clientes
│   ├── member.py           # Membres/Clients
│   ├── reservation.py      # Réservations
│   ├── service.py          # Services
│   ├── travel.py           # Destinations/Voyages
│   ├── credit.py           # Système de crédit
│   ├── invoice_client.py   # Factures clients
│   ├── invoice.py          # Extension account.move
│   ├── purchase.py         # Extension purchase.order
│   ├── purchase_travel.py  # Factures fournisseurs
│   ├── purchase_report.py  # Rapports achats
│   ├── partner.py          # Extension res.partner
│   ├── pos.py              # Extension POS
│   ├── cash_register.py    # Gestion des caisses
│   ├── cash_register_operation.py  # Opérations caisse
│   └── withholding.py      # Retenues à la source
├── views/                   # Vues XML
├── security/               # Sécurité
│   ├── security.xml        # Groupes et règles
│   └── ir.model.access.csv # Droits d'accès
├── data/                   # Données initiales
├── tests/                  # Tests unitaires
├── static/                 # Assets (CSS, images)
└── doc/                    # Documentation
```

### Diagramme des Relations

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MODÈLES PRINCIPAUX                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐                                                    │
│  │  travel.company  │◄───────────────────────────────────┐              │
│  │  (Société)       │                                    │              │
│  └────────┬─────────┘                                    │              │
│           │ One2many                                     │              │
│           ▼                                              │              │
│  ┌──────────────────┐         ┌──────────────────┐      │              │
│  │  travel.member   │────────►│   res.partner    │      │              │
│  │  (Membre/Client) │Many2one │   (Contact)      │      │              │
│  └────────┬─────────┘         └──────────────────┘      │              │
│           │ One2many                                     │              │
│           ▼                                              │              │
│  ┌──────────────────┐         ┌──────────────────┐      │              │
│  │travel.reservation│────────►│travel.destination│      │              │
│  │  (Réservation)   │Many2one │   (Voyage)       │      │              │
│  └────────┬─────────┘         └────────┬─────────┘      │              │
│           │                            │ Many2many      │              │
│           │                            ▼                │              │
│           │                   ┌──────────────────┐      │              │
│           │                   │  travel.service  │──────┘              │
│           │                   │   (Service)      │ Many2one            │
│           │                   └──────────────────┘ supplier_id         │
│           │                                                            │
│           ├───────────────────────────────────────────────────┐       │
│           │ One2many                                          │       │
│           ▼                                                   ▼       │
│  ┌──────────────────┐                              ┌─────────────────┐│
│  │   account.move   │                              │cash.register.op ││
│  │   (Facture)      │                              │(Opération Caisse││
│  └──────────────────┘                              └─────────────────┘│
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Modèles de Données

### 3.1 travel.company (Société Cliente)

**Description**: Gère les entreprises clientes de l'agence.

| Champ | Type | Description |
|-------|------|-------------|
| name | Char | Nom de la société (unique) |
| vat | Char | Matricule fiscal (unique) |
| email | Char | Email de contact |
| phone | Char | Téléphone fixe |
| mobile | Char | Téléphone mobile |
| address | Text | Adresse complète |
| website | Char | Site web |
| member_ids | One2many | Membres de la société |
| member_count | Integer | Nombre de membres (calculé) |

**Contraintes SQL**:
- `name_unique`: Nom unique
- `vat_unique`: Matricule fiscal unique

**Validations**:
- Email: Format RFC 5322
- VAT: Format tunisien (avertissement si non standard)

---

### 3.2 travel.member (Membre/Client)

**Description**: Gère les clients individuels de l'agence.

| Champ | Type | Description |
|-------|------|-------------|
| name | Char | Nom complet (requis) |
| company_id | Many2one | Société parente |
| email | Char | Email |
| phone | Char | Téléphone |
| matricule | Char | Identifiant unique |
| partner_id | Many2one | Contact Odoo associé |
| credit_balance | Float | Solde crédit (calculé) |
| reservation_ids | One2many | Réservations |

**Contraintes SQL**:
- `matricule_unique`: Matricule unique
- `partner_unique`: Un partner = un membre

**Comportements automatiques**:
- Création automatique du `res.partner` si non fourni
- Synchronisation nom/email/phone vers le partner

---

### 3.3 travel.reservation (Réservation)

**Description**: Gère les réservations de voyages.

| Champ | Type | Description |
|-------|------|-------------|
| name | Char | Référence (séquence auto) |
| member_id | Many2one | Client (requis) |
| destination_id | Many2one | Voyage/Destination |
| trip_type | Selection | Type: hotel, voyage_organise, billetrie, autre |
| check_in | Date | Date d'arrivée |
| check_out | Date | Date de départ |
| nights | Integer | Nuitées (calculé) |
| adults | Integer | Nombre d'adultes |
| children | Integer | Nombre d'enfants |
| infants | Integer | Nombre de bébés |
| price | Float | Prix du voyage TTC |
| total_price | Float | Total avec services |
| status | Selection | draft, confirmed, done, cancel |
| use_credit | Boolean | Utiliser le crédit client |
| credit_used | Float | Montant crédit utilisé |
| remaining_to_pay | Float | Reste à payer |

**Workflow**:
```
draft ──► confirmed ──► done
   │                      │
   └──────► cancel ◄──────┘
```

---

### 3.4 travel.invoice.client (Facture Client)

**Description**: Factures clients avec calculs TVA tunisiens.

| Champ | Type | Description |
|-------|------|-------------|
| name | Char | Numéro facture (séquence) |
| date_invoice | Date | Date facture |
| travel_company_id | Many2one | Société cliente |
| member_ids | Many2many | Membres facturés |
| amount_untaxed | Monetary | Total HT |
| amount_tax | Monetary | Total TVA |
| fiscal_stamp | Monetary | Timbre fiscal (1 TND) |
| amount_total | Monetary | Total TTC |
| discount_type | Selection | none, percent, fixed |
| discount_rate | Float | Taux remise % |
| apply_withholding_tax | Boolean | Retenue 1% |
| apply_vat_withholding | Boolean | Retenue 25% TVA |
| net_to_pay | Monetary | Net à payer |
| state | Selection | draft, confirmed, paid, cancel |

**Formules de calcul**:
```python
# Calcul depuis TTC
HT = TTC / (1 + taux_TVA)
TVA = HT × taux_TVA

# Avec remise
HT_après_remise = HT - remise
TVA = HT_après_remise × taux_TVA
Total = HT_après_remise + TVA + timbre_fiscal

# Retenues
Retenue_1% = (Total - timbre) × 0.01
Retenue_25%_TVA = TVA × 0.25
Net = Total - Retenues
```

---

### 3.5 cash.register (Caisse)

**Description**: Gestion des caisses avec hiérarchie principale/sous-caisses.

| Champ | Type | Description |
|-------|------|-------------|
| name | Char | Nom de la caisse |
| code | Char | Code unique |
| is_main | Boolean | Est caisse principale |
| main_cash_id | Many2one | Caisse principale parente |
| state | Selection | closed, opened |
| opening_balance | Float | Solde d'ouverture |
| balance | Float | Solde actuel (calculé) |
| total_receipts | Float | Total recettes |
| total_expenses | Float | Total dépenses |

**Règles métier**:
- Une seule caisse principale par société
- Maximum 2 sous-caisses par caisse principale
- Sous-caisse ne peut ouvrir que si principale ouverte
- Principale ne peut fermer que si sous-caisses fermées

---

## 4. Système de Sécurité

### 4.1 Groupes d'Utilisateurs

| Groupe | ID XML | Permissions |
|--------|--------|-------------|
| **Agent de Voyage** | `group_travel_user` | CRUD membres, réservations, factures (pas de suppression) |
| **Responsable Agence** | `group_travel_manager` | Accès complet + gestion caisses |
| **Comptable Agence** | `group_travel_accountant` | Factures fournisseurs, retenues |

### 4.2 Hiérarchie des Groupes

```
base.group_user
       │
       ▼
group_travel_user ◄────────────┐
       │                       │
       ├──► group_travel_manager
       │
       └──► group_travel_accountant
```

### 4.3 Matrice des Droits d'Accès

| Modèle | User R/W/C | User D | Manager D | Comptable |
|--------|------------|--------|-----------|-----------|
| travel.company | ✅/✅/✅ | ❌ | ✅ | - |
| travel.member | ✅/✅/✅ | ❌ | ✅ | - |
| travel.reservation | ✅/✅/✅ | ❌ | ✅ | - |
| cash.register | ✅/❌/❌ | ❌ | ✅ | - |
| cash.register.operation | ✅/✅/✅ | ❌ | ✅ | - |
| travel.invoice.client | ✅/✅/✅ | ❌ | ✅ | ✅ |
| travel.purchase | ❌ | ❌ | ✅ | ✅ |
| travel.withholding | ❌ | ❌ | ✅ | ✅ |

---

## 5. Flux Métier

### 5.1 Flux de Réservation Complet

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FLUX DE RÉSERVATION                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. CRÉATION CLIENT                                                      │
│     ┌────────────────┐     ┌────────────────┐                           │
│     │ Créer Société  │────►│ Créer Membre   │                           │
│     │ travel.company │     │ travel.member  │                           │
│     └────────────────┘     └───────┬────────┘                           │
│                                    │                                     │
│  2. RÉSERVATION                    ▼                                     │
│     ┌────────────────────────────────────────────────────┐              │
│     │ Créer Réservation (status: draft)                  │              │
│     │ - Sélectionner destination                         │              │
│     │ - Dates check-in/check-out auto-remplies          │              │
│     │ - Prix auto-rempli depuis destination             │              │
│     └───────────────────────────┬────────────────────────┘              │
│                                 │                                        │
│  3. CONFIRMATION                ▼                                        │
│     ┌────────────────────────────────────────────────────┐              │
│     │ action_confirm() → status: confirmed               │              │
│     └───────────────────────────┬────────────────────────┘              │
│                                 │                                        │
│  4. FACTURATION                 ▼                                        │
│     ┌────────────────────────────────────────────────────┐              │
│     │ action_create_invoice()                            │              │
│     │ - Crée travel.invoice.client                       │              │
│     │ - Crée ligne avec prix réservation                │              │
│     │ - Calcule TVA automatiquement                     │              │
│     └───────────────────────────┬────────────────────────┘              │
│                                 │                                        │
│  5. PAIEMENT                    ▼                                        │
│     ┌────────────────────────────────────────────────────┐              │
│     │ Options de paiement:                               │              │
│     │ a) action_pay_cash() → Opération de caisse        │              │
│     │ b) action_open_pos() → Paiement POS               │              │
│     │ c) Utilisation crédit client                      │              │
│     └───────────────────────────┬────────────────────────┘              │
│                                 │                                        │
│  6. CLÔTURE                     ▼                                        │
│     ┌────────────────────────────────────────────────────┐              │
│     │ action_done() → status: done                       │              │
│     │ OU                                                 │              │
│     │ action_cancel_and_credit() → status: cancel        │              │
│     │ (Remboursement automatique en crédit)             │              │
│     └────────────────────────────────────────────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Flux de Caisse

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FLUX DE CAISSE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  MATIN - OUVERTURE                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 1. Manager ouvre la caisse principale                           │    │
│  │    action_open_cash()                                           │    │
│  │ 2. Les sous-caisses s'ouvrent automatiquement                   │    │
│  │ 3. Solde d'ouverture = balance précédente (si > 0)              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  JOURNÉE - OPÉRATIONS                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Agent crée opération (type: receipt ou expense)                 │    │
│  │ - Lier à réservation/facture si applicable                     │    │
│  │ - Confirmer l'opération                                         │    │
│  │ - Imprimer reçu automatiquement (si recette)                   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  SOIR - FERMETURE                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ 1. Chaque agent ferme sa sous-caisse                            │    │
│  │    action_close_sub_cash()                                      │    │
│  │ 2. Manager vérifie les soldes                                   │    │
│  │ 3. Manager ferme la caisse principale                           │    │
│  │    action_close_cash()                                          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  AUTOMATIQUE - MINUIT                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Cron: cron_close_main_cash_at_midnight()                        │    │
│  │ Fermeture automatique si oubli                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. API et Intégrations

### 6.1 Méthodes Publiques Principales

#### travel.reservation
```python
def action_confirm(self)
    """Confirme la réservation (draft → confirmed)"""

def action_create_invoice(self)
    """Crée une facture client depuis la réservation
    
    Returns:
        dict: Action window vers la facture créée
    
    Raises:
        UserError: Si membre sans société
    """

def action_cancel_and_credit(self)
    """Annule et rembourse en crédit client"""

def action_open_pos(self)
    """Ouvre le formulaire de paiement caisse"""
```

#### travel.invoice.client
```python
def action_confirm(self)
    """Confirme la facture (nécessite au moins une ligne)"""

def action_pay_cash(self)
    """Ouvre le formulaire d'opération de caisse"""

def action_fill_lines_from_selected_members(self)
    """Remplit automatiquement les lignes depuis les réservations"""
```

#### cash.register
```python
def action_open_cash(self)
    """Ouvre la caisse (et sous-caisses si principale)"""

def action_close_cash(self)
    """Ferme la caisse principale"""

def action_close_sub_cash(self)
    """Ferme une sous-caisse"""
```

### 6.2 Hooks et Signaux

```python
# __init__.py
def post_init_hook(cr, registry):
    """
    Configure la devise TND après installation.
    Exécuté uniquement si aucune écriture comptable n'existe.
    """
```

---

## 7. Tests

### 7.1 Structure des Tests

```
tests/
├── __init__.py
├── test_member.py           # 12 tests
├── test_company.py          # 10 tests
├── test_reservation.py      # 15 tests
├── test_invoice_client.py   # 14 tests
├── test_cash_register.py    # 15 tests
└── test_credit.py           # 9 tests
```

### 7.2 Exécution des Tests

```bash
# Tous les tests du module
./odoo-bin -c odoo.conf -i travel_pro_version1 --test-enable --stop-after-init

# Un fichier de test spécifique
./odoo-bin -c odoo.conf -i travel_pro_version1 --test-file=addons/travel_pro_version1/tests/test_member.py --stop-after-init

# Avec couverture de code
pip install coverage
coverage run ./odoo-bin -c odoo.conf -i travel_pro_version1 --test-enable --stop-after-init
coverage report -m
```

### 7.3 Couverture Visée

| Module | Couverture Cible |
|--------|------------------|
| member.py | 90%+ |
| company.py | 85%+ |
| reservation.py | 85%+ |
| invoice_client.py | 80%+ |
| cash_register.py | 85%+ |

---

## 8. Installation et Configuration

### 8.1 Prérequis

```bash
# Dépendances Python
pip install num2words  # Conversion montants en lettres
```

### 8.2 Installation

```bash
# 1. Copier le module dans le dossier addons
cp -r travel_pro_version1 /path/to/odoo/addons/

# 2. Mettre à jour la liste des modules
./odoo-bin -c odoo.conf -u base --stop-after-init

# 3. Installer le module
./odoo-bin -c odoo.conf -i travel_pro_version1 --stop-after-init
```

### 8.3 Mise à Jour

```bash
# Mise à jour du module
./odoo-bin -c odoo.conf -u travel_pro_version1 --stop-after-init
```

### 8.4 Configuration Post-Installation

1. **Créer les séquences** (automatique via data/)
2. **Configurer la caisse principale**:
   - Aller dans TravelPro > Caisse > Caisses
   - Créer une caisse principale
   - Créer les sous-caisses (max 2)
3. **Assigner les groupes de sécurité**:
   - Aller dans Paramètres > Utilisateurs
   - Assigner les groupes TravelPro

---

## 9. Maintenance

### 9.1 Logs Importants

```python
# Activer les logs du module
import logging
_logger = logging.getLogger(__name__)

# Niveaux de log utilisés:
_logger.debug("...")   # Détails techniques
_logger.info("...")    # Actions importantes
_logger.warning("...")  # Situations anormales
_logger.error("...")   # Erreurs à investiguer
```

### 9.2 Problèmes Courants

| Problème | Cause | Solution |
|----------|-------|----------|
| Erreur devise TND | Devise non active | Activer TND dans Paramètres > Devises |
| Partner not found | Membre sans contact | Recréer le membre |
| Caisse fermée | Tentative opération | Ouvrir la caisse principale |
| Facture sans lignes | Confirmation prématurée | Ajouter des lignes d'abord |

### 9.3 Sauvegarde Recommandée

```bash
# Tables critiques
pg_dump -t travel_company \
        -t travel_member \
        -t travel_reservation \
        -t travel_invoice_client \
        -t travel_invoice_client_line \
        -t cash_register \
        -t cash_register_operation \
        -t travel_credit_history \
        database_name > backup.sql
```

---

## Annexes

### A. Glossaire

| Terme | Définition |
|-------|------------|
| **Membre** | Client individuel de l'agence |
| **Société** | Entreprise cliente (groupe de membres) |
| **Destination** | Voyage/séjour proposé |
| **Service** | Prestation (hébergement, transport, etc.) |
| **Caisse principale** | Caisse centrale de l'agence |
| **Sous-caisse** | Caisse d'un agent (dépend de la principale) |
| **Retenue** | Prélèvement fiscal sur les paiements |

### B. Contacts Support

- **Technique**: dev@we-cantravel.com
- **Documentation**: https://we-cantravel.com/docs

---

*Document généré le: 2024*
*Version: 16.0.4.0*

