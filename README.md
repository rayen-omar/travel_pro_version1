# 🎯 TravelPro - Module Odoo 16 pour Agences de Voyage

## 📌 Description

**TravelPro** est un module ERP complet pour la gestion d'agences de voyage, développé pour Odoo 16. Il permet de gérer :

✅ **Réservations complètes** (hébergement + vols + services)
✅ **Workflow d'approbation** multi-niveaux
✅ **Gestion des passagers** et documents de voyage
✅ **Paiements partiels** et acomptes
✅ **Système de crédit client**
✅ **Commissions fournisseurs**
✅ **Intégration complète** avec Ventes, Achats, Comptabilité et POS

---

## 🚀 Installation

### Pré-requis
- Odoo 16.0
- Python 3.8+
- Modules dépendants : `base`, `sale`, `account`, `purchase`, `point_of_sale`, `mail`

### Étapes d'installation

1. **Copier le module** dans votre dossier addons Odoo :
```bash
cp -r travel_pro_version1 /path/to/odoo/addons/
```

2. **Mettre à jour la liste des applications** :
   - Aller dans Odoo → Apps → Update Apps List

3. **Installer le module** :
   - Rechercher "TravelPro"
   - Cliquer sur "Install"

---

## 📂 Structure du Module

```
travel_pro_version1/
├── __init__.py
├── __manifest__.py
├── data/
│   ├── sequence_data.xml        # Séquences pour numérotation auto
│   └── pos_config.xml           # Configuration Point de Vente
├── models/
│   ├── __init__.py
│   ├── reservation.py           # ⭐ Réservations (cœur du système)
│   ├── flight.py                # ✈️ Gestion des vols
│   ├── passenger.py             # 👤 Passagers et documents
│   ├── member.py                # Clients/Membres
│   ├── travel.py                # Destinations
│   ├── service.py               # Services additionnels
│   ├── credit.py                # Système de crédit
│   ├── company.py               # Sociétés clientes
│   ├── purchase.py              # Extension achats
│   ├── invoice.py               # Extension factures
│   ├── pos.py                   # Extension POS
│   └── partner.py               # Extension contacts
├── views/
│   ├── reservation_views.xml    # Vues principales réservations
│   ├── member_views.xml         # Vues clients
│   ├── travel_views.xml         # Vues destinations
│   ├── service_views.xml        # Vues services
│   ├── credit_views.xml         # Vues crédit
│   ├── purchase_views.xml       # Vues achats
│   ├── invoice_views.xml        # Vues factures
│   ├── pos_views.xml            # Vues POS
│   ├── company_views.xml        # Vues sociétés
│   └── menu.xml                 # Menu principal
├── security/
│   └── ir.model.access.csv      # Droits d'accès
└── AMELIORATIONS.md             # 📖 Document d'analyse et améliorations
```

---

## 🎯 Fonctionnalités Principales

### 1️⃣ Gestion des Réservations

**Workflow Complet :**
```
Brouillon → En Attente → Validé → Confirmé → En Cours → Terminé
```

**Caractéristiques :**
- Hébergement (nuitées, catégorie chambre, type)
- Vols (aller-retour, classe, bagages)
- Services additionnels
- Calcul automatique des prix et marges
- Gestion des participants (adultes, enfants, bébés)

**Actions disponibles :**
- ✅ Créer devis de vente
- ✅ Créer commande d'achat fournisseur
- ✅ Générer facture
- ✅ Enregistrer paiement (POS)
- ✅ Appliquer crédit client
- ✅ Annuler et créditer

### 2️⃣ Workflow d'Approbation

**3 Niveaux de validation :**

| Rôle | Actions | Seuil |
|------|---------|-------|
| **Agent** | Créer, Soumettre | - |
| **Manager** | Valider | < 5000€ |
| **Directeur** | Confirmer définitivement | > 5000€ |

**Notifications automatiques :**
- À chaque changement de statut
- Rappels avant départ (7 jours)
- Alertes documents expirés

### 3️⃣ Gestion des Passagers

**Informations collectées :**
- État civil complet
- Documents (passeport, visa, CI)
- Préférences (repas, siège, assistance)
- Programmes de fidélité
- Conditions médicales

**Validations automatiques :**
- ✅ Passeport valide 6 mois après retour
- ✅ Visa en cours si requis
- ✅ Âge correct (adulte/enfant/bébé)

### 4️⃣ Gestion des Vols

**Types supportés :**
- Aller simple
- Aller-retour
- Multi-destinations (avec escales)

**Informations :**
- Compagnie aérienne, n° de vol
- Horaires départ/arrivée
- Classe (économique, affaires, première)
- Bagages (cabine, soute)
- PNR / Référence réservation

### 5️⃣ Système de Crédit Client

**Fonctionnalités :**
- Recharge manuelle
- Crédit automatique en cas d'annulation
- Utilisation à la réservation
- Historique complet des mouvements

**Types de mouvement :**
- 💰 Recharge manuelle
- 🔄 Remboursement annulation
- 📉 Utilisation réservation

### 6️⃣ Paiements et Acomptes

**Méthodes de paiement :**
- Espèces
- Carte bancaire
- Virement
- Chèque
- Crédit client

**Gestion des acomptes :**
- Pourcentage configurable (défaut 30%)
- Suivi solde dû
- Paiements partiels multiples
- Statut : Non payé / Partiellement payé / Payé

### 7️⃣ Documents de Voyage

**Types de documents :**
- 🛂 Passeport
- 🛂 Visa
- 🎫 Billets
- 📄 Vouchers/Bons
- 🏥 Assurance
- 📝 Contrats
- 🧾 Factures

**Gestion automatique :**
- Alertes d'expiration (30 jours avant)
- Statut de vérification
- Stockage sécurisé (attachments)

### 8️⃣ Commissions Fournisseurs

**Calcul :**
- Pourcentage ou montant fixe
- Base configurable
- Validation multi-niveaux

**Statuts :**
- En attente
- Approuvé
- Payé

---

## 👥 Groupes Utilisateurs

| Groupe | Droits |
|--------|--------|
| **Agent de Voyage** | Créer et voir ses réservations |
| **Manager Agence** | Voir toutes réservations, Valider < 5000€ |
| **Directeur Agence** | Tous droits, Confirmer toutes réservations |

---

## 🔧 Configuration Post-Installation

### 1. Créer les Groupes Utilisateurs

```
Paramètres → Utilisateurs & Sociétés → Groupes
```

Créer :
- `Agent de Voyage`
- `Manager Agence` (hérite de Agent)
- `Directeur Agence` (hérite de Manager)

### 2. Configurer les Séquences

```
Paramètres → Technique → Séquences
```

Vérifier :
- `travel.reservation` → Format : RES/%(year)s/%(month)s/%(seq)s

### 3. Créer les Destinations

```
Voyage → Configuration → Destinations
```

Exemple :
- Paris, France
- Londres, UK
- Dubai, UAE
- New York, USA

### 4. Créer les Services

```
Voyage → Configuration → Services
```

Types :
- Hébergement (hôtels)
- Transport (navettes, location voiture)
- Activités (excursions, visites)

### 5. Configurer le Point de Vente

```
Point de Vente → Configuration → Points de Vente
```

Un POS dédié "Caisse Agence" est créé automatiquement.

---

## 📊 Rapports Disponibles

### Tableau de Bord
- CA Total
- Nombre de réservations
- Ticket moyen
- Taux d'occupation

### Rapports Analytiques
- Réservations par destination
- Réservations par client
- Marges par période
- Commissions par fournisseur

### Exports
- Liste clients
- Historique réservations
- États financiers

---

## 🔄 Workflow Typique

### Scénario : Nouvelle Réservation

1. **Agent crée une réservation**
   - Client : Dupont Jean
   - Destination : Paris
   - Dates : 15-20 Dec 2024
   - Hébergement : Hôtel Marriott
   - Vol : Paris → New York

2. **Agent soumet pour validation**
   - Statut : `En Attente Validation`
   - Notification → Manager

3. **Manager valide**
   - Vérifie prix et disponibilité
   - Statut : `Validé Manager`
   - Si > 5000€ → Notification Directeur

4. **Directeur confirme** (si requis)
   - Statut : `Confirmé`
   - Création automatique du devis

5. **Agent finalise**
   - Crée commande achat fournisseur
   - Génère facture client
   - Enregistre acompte (30%)

6. **Avant départ**
   - Rappel automatique 7 jours avant
   - Vérification documents passagers

7. **Après voyage**
   - Paiement solde
   - Statut : `Terminé`

---

## 🐛 Dépannage

### Problème : Impossible de créer un membre

**Cause** : Contrainte company_id sur res.partner

**Solution** :
```python
# Dans member.py, ligne 38
partner = self.env['res.partner'].with_context(default_company_id=False).create(partner_vals)
```

### Problème : Erreur de séquence

**Solution** :
```xml
<!-- Dans data/sequence_data.xml -->
<record id="seq_travel_reservation" model="ir.sequence">
    <field name="name">Réservation Voyage</field>
    <field name="code">travel.reservation</field>
    <field name="prefix">RES/%(year)s/</field>
    <field name="padding">5</field>
</record>
```

### Problème : POS ne s'ouvre pas

**Vérifier** :
- Config POS existe : `travel_pro_version1.pos_config_travel`
- Session POS ouverte
- Droits utilisateur

---

## 📈 Améliorations Futures

Voir le fichier **AMELIORATIONS.md** pour :
- ✨ Nouvelles fonctionnalités proposées
- 🔧 Optimisations techniques
- 📱 Améliorations UI/UX
- 🔌 Intégrations API externes

### Priorités :
1. **Dashboard graphique** avec KPI
2. **Vue Kanban** pour réservations
3. **Intégration Amadeus API** pour réservation vols
4. **Module mobile** pour agents terrain
5. **Reporting avancé** avec graphiques

---

## 📞 Support & Contact

### Documentation
- Odoo Official : https://www.odoo.com/documentation/16.0/
- ORM API : https://www.odoo.com/documentation/16.0/developer/reference/backend/orm.html

### Développeur
- Auteur : Votre Agence
- Version : 16.0.1.0
- License : OPL-1

---

## 📝 Notes de Version

### v16.0.1.0 (Version Actuelle)
- ✅ Réservations de base
- ✅ Système de crédit
- ✅ Intégration POS
- ✅ Gestion membres/clients

### v16.0.2.0 (Planifié)
- 🚀 Workflow d'approbation complet
- 🚀 Gestion vols
- 🚀 Gestion passagers
- 🚀 Documents voyage

### v16.0.3.0 (Future)
- 🔮 Dashboard analytics
- 🔮 Rapports avancés
- 🔮 API externe
- 🔮 Application mobile

---

## ⚖️ Licence

**Odoo Proprietary License v1.0**

Ce module est propriétaire. Toute utilisation, modification ou distribution nécessite une licence commerciale.

---

## 🙏 Remerciements

Merci à la communauté Odoo pour leur excellent framework ERP !

---

**Bonne utilisation de TravelPro ! ✈️🌍**
