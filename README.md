# 🌍 TravelPro ERP - Module Odoo 16

[![Version](https://img.shields.io/badge/version-16.0.4.0-blue.svg)](https://github.com/we-can-travel/travel-pro)
[![Odoo](https://img.shields.io/badge/Odoo-16.0-purple.svg)](https://www.odoo.com/)
[![License](https://img.shields.io/badge/license-OPL--1-red.svg)](LICENSE)

Module complet de gestion pour agences de voyage sous Odoo 16 Community.

## ✨ Fonctionnalités

### 👥 Gestion Clients
- **Sociétés**: Entreprises clientes avec informations fiscales
- **Membres**: Clients individuels avec système de crédit
- **Synchronisation**: Liaison automatique avec `res.partner`

### ✈️ Réservations
- **Types**: Hôtel, Voyage organisé, Billetrie
- **Workflow**: Brouillon → Confirmé → Terminé/Annulé
- **Services**: Hébergement, Transport, Activités

### 💰 Facturation
- **Factures Clients**: Calcul TVA tunisienne (7%, 19%)
- **Factures Fournisseurs**: Gestion complète des achats
- **Retenues**: 1% sur TTC, 25% sur TVA
- **Remises**: Pourcentage ou montant fixe

### 🏦 Caisse
- **Hiérarchie**: Caisse principale + sous-caisses (max 2)
- **Opérations**: Recettes et dépenses avec reçus
- **Contrôle**: Ouverture/fermeture avec soldes

### 📊 Rapports
- Devis de réservation
- Factures clients
- Factures fournisseurs
- Reçus de caisse

## 🚀 Installation

### Prérequis
    ```bash
# Python 3.10+
    pip install num2words
    ```

### Installation du module
```bash
# Copier dans le dossier addons
cp -r travel_pro_version1 /path/to/odoo/addons/

# Installer
./odoo-bin -c odoo.conf -i travel_pro_version1
```

### Mise à jour
```bash
./odoo-bin -c odoo.conf -u travel_pro_version1
```

## 🔐 Sécurité

### Groupes d'utilisateurs
| Groupe | Description |
|--------|-------------|
| **Agent de Voyage** | Opérations quotidiennes (pas de suppression) |
| **Responsable Agence** | Accès complet + gestion caisses |
| **Comptable Agence** | Factures fournisseurs + retenues |

## 📁 Structure

```
travel_pro_version1/
├── models/          # Modèles Python (16 fichiers)
├── views/           # Vues XML (21 fichiers)
├── security/        # Groupes et droits d'accès
├── data/            # Séquences et données initiales
├── tests/           # Tests unitaires (~75 tests)
├── static/          # CSS et images
└── doc/             # Documentation technique
```

## 🧪 Tests

```bash
# Exécuter tous les tests
./odoo-bin -c odoo.conf -i travel_pro_version1 --test-enable --stop-after-init
```

## 📖 Documentation

Voir [doc/DOCUMENTATION_TECHNIQUE.md](doc/DOCUMENTATION_TECHNIQUE.md) pour la documentation complète.

## 📝 Changelog

### v16.0.4.0 (Current)
- ✅ Ajout groupes de sécurité
- ✅ Ajout record rules
- ✅ Ajout SQL constraints
- ✅ Validations email/téléphone
- ✅ Corrections exceptions silencieuses
- ✅ Tests unitaires (~75 tests)
- ✅ Documentation technique

### v16.0.3.0
- Gestion des caisses avec sous-caisses
- Factures clients avec retenues
- Système de crédit client

## 🤝 Support

- **Email**: dev@we-cantravel.com
- **Site**: https://we-cantravel.com

## 📄 Licence

Ce module est sous licence propriétaire OPL-1.

---

*Développé par WE CAN TRAVEL © 2024*
