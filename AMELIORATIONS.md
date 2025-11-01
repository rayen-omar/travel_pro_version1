# 🚀 Analyse & Améliorations - Module TravelPro

## 📊 État Actuel du Module

### ✅ Points Forts
- Structure Odoo bien organisée (models, views, security)
- Système de crédit client fonctionnel
- Intégration avec Ventes, Achats, Comptabilité et Point de Vente
- Workflow de base : Réservation → Devis → Facture → Paiement
- Tracking avec mail.thread
- Calculs automatiques (nuitées, participants, totaux)

### ⚠️ Limites Identifiées
1. **Pas de workflow d'approbation** (validation multi-niveaux)
2. **Gestion des vols/trains absente** (seulement hébergement)
3. **Pas de gestion documentaire** (passeports, visas, contrats)
4. **Rapports et statistiques limités**
5. **Pas de notifications automatiques**
6. **Sécurité basique** (pas de groupes utilisateurs spécifiques)
7. **Pas d'intégration API externes** (réservations en ligne)
8. **Gestion des commissions fournisseurs manquante**
9. **Pas de gestion des acomptes/paiements partiels**
10. **Interface utilisateur basique**

---

## 🎯 Propositions d'Amélioration

### 1️⃣ PRIORITÉ HAUTE : Workflow d'Approbation

**Problème** : Actuellement, les réservations passent directement de "brouillon" à "confirmé" sans validation.

**Solution** :
- Ajouter des états intermédiaires : `draft` → `pending` → `validated` → `confirmed` → `done`
- Créer des groupes utilisateurs : Agent, Manager, Director
- Workflow configurable selon le montant
- Notifications automatiques à chaque étape

**Code à ajouter** :
```python
# Dans reservation.py
status = fields.Selection([
    ('draft', 'Brouillon'),
    ('pending', 'En attente validation'),
    ('validated', 'Validé Manager'),
    ('confirmed', 'Confirmé'),
    ('done', 'Terminé'),
    ('cancel', 'Annulé')
], default='draft', tracking=True)

approval_user_id = fields.Many2one('res.users', string='Validé par')
approval_date = fields.Datetime('Date validation')

def action_submit_for_approval(self):
    """Soumettre pour approbation"""
    self.status = 'pending'
    # Envoyer notification au manager

def action_approve(self):
    """Approuver la réservation (Manager)"""
    self.status = 'validated'
    self.approval_user_id = self.env.user
    self.approval_date = fields.Datetime.now()

def action_confirm(self):
    """Confirmer définitivement (Director)"""
    self.status = 'confirmed'
```

---

### 2️⃣ PRIORITÉ HAUTE : Gestion Complète des Voyages

**Ajouter un modèle `travel.flight` pour les vols** :

```python
class TravelFlight(models.Model):
    _name = 'travel.flight'
    _description = 'Vol'
    
    reservation_id = fields.Many2one('travel.reservation', 'Réservation')
    flight_type = fields.Selection([
        ('oneway', 'Aller Simple'),
        ('roundtrip', 'Aller-Retour'),
        ('multi', 'Multi-destinations')
    ], 'Type', required=True)
    
    # Vol Aller
    departure_city = fields.Char('Ville départ', required=True)
    arrival_city = fields.Char('Ville arrivée', required=True)
    departure_date = fields.Datetime('Date départ')
    arrival_date = fields.Datetime('Date arrivée')
    flight_number = fields.Char('N° Vol')
    airline = fields.Many2one('res.partner', 'Compagnie', domain="[('is_company', '=', True)]")
    
    # Vol Retour (si applicable)
    return_departure_date = fields.Datetime('Date départ retour')
    return_arrival_date = fields.Datetime('Date arrivée retour')
    return_flight_number = fields.Char('N° Vol retour')
    
    # Tarifs
    class_type = fields.Selection([
        ('economy', 'Économique'),
        ('premium', 'Premium'),
        ('business', 'Affaires'),
        ('first', 'Première')
    ], 'Classe')
    purchase_price = fields.Float('Prix achat')
    sale_price = fields.Float('Prix vente')
    baggage_allowance = fields.Char('Bagages inclus')
    
    passenger_ids = fields.One2many('travel.passenger', 'flight_id', 'Passagers')
```

**Ajouter `travel.passenger` pour les passagers** :

```python
class TravelPassenger(models.Model):
    _name = 'travel.passenger'
    _description = 'Passager'
    
    reservation_id = fields.Many2one('travel.reservation', 'Réservation')
    flight_id = fields.Many2one('travel.flight', 'Vol')
    
    name = fields.Char('Nom complet', required=True)
    first_name = fields.Char('Prénom', required=True)
    last_name = fields.Char('Nom', required=True)
    birth_date = fields.Date('Date naissance')
    gender = fields.Selection([('male', 'M'), ('female', 'F')], 'Sexe')
    
    # Documents
    passport_number = fields.Char('N° Passeport')
    passport_expiry = fields.Date('Expiration passeport')
    passport_country_id = fields.Many2one('res.country', 'Pays passeport')
    visa_required = fields.Boolean('Visa requis')
    visa_status = fields.Selection([
        ('not_required', 'Non requis'),
        ('pending', 'En cours'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé')
    ], 'Statut visa')
    
    # Infos supplémentaires
    frequent_flyer_number = fields.Char('N° Programme fidélité')
    special_meal = fields.Selection([
        ('none', 'Aucun'),
        ('vegetarian', 'Végétarien'),
        ('vegan', 'Végétalien'),
        ('halal', 'Halal'),
        ('kosher', 'Casher')
    ], 'Repas spécial')
    special_assistance = fields.Text('Assistance spéciale')
```

---

### 3️⃣ PRIORITÉ MOYENNE : Gestion Documentaire

**Ajouter un modèle `travel.document`** :

```python
class TravelDocument(models.Model):
    _name = 'travel.document'
    _description = 'Document Voyage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char('Nom document', required=True)
    reservation_id = fields.Many2one('travel.reservation', 'Réservation')
    passenger_id = fields.Many2one('travel.passenger', 'Passager')
    
    document_type = fields.Selection([
        ('passport', 'Passeport'),
        ('visa', 'Visa'),
        ('ticket', 'Billet'),
        ('voucher', 'Bon/Voucher'),
        ('insurance', 'Assurance'),
        ('contract', 'Contrat'),
        ('invoice', 'Facture'),
        ('other', 'Autre')
    ], 'Type', required=True)
    
    file_data = fields.Binary('Fichier', attachment=True)
    file_name = fields.Char('Nom fichier')
    
    issue_date = fields.Date('Date émission')
    expiry_date = fields.Date('Date expiration')
    
    status = fields.Selection([
        ('pending', 'En attente'),
        ('received', 'Reçu'),
        ('verified', 'Vérifié'),
        ('expired', 'Expiré')
    ], 'Statut', default='pending', tracking=True)
    
    note = fields.Text('Notes')
    
    @api.model
    def _cron_check_expiry(self):
        """Vérifier les documents expirés ou sur le point d'expirer"""
        today = fields.Date.today()
        warning_date = today + timedelta(days=30)
        
        expiring_docs = self.search([
            ('expiry_date', '<=', warning_date),
            ('expiry_date', '>=', today),
            ('status', '!=', 'expired')
        ])
        
        for doc in expiring_docs:
            # Envoyer notification
            doc.message_post(
                body=f"⚠️ Le document {doc.name} expire le {doc.expiry_date}",
                subject="Document en expiration",
            )
```

---

### 4️⃣ PRIORITÉ MOYENNE : Gestion des Paiements Partiels

**Améliorer le modèle de paiement** :

```python
class TravelPayment(models.Model):
    _name = 'travel.payment'
    _description = 'Paiement Réservation'
    _order = 'date desc'
    
    reservation_id = fields.Many2one('travel.reservation', 'Réservation', required=True)
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    amount = fields.Float('Montant', required=True)
    
    payment_method = fields.Selection([
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('transfer', 'Virement'),
        ('check', 'Chèque'),
        ('credit', 'Crédit client')
    ], 'Méthode', required=True)
    
    reference = fields.Char('Référence')
    note = fields.Text('Note')
    
    invoice_id = fields.Many2one('account.move', 'Facture liée')
    pos_order_id = fields.Many2one('pos.order', 'Commande POS')

# Dans reservation.py ajouter :
payment_ids = fields.One2many('travel.payment', 'reservation_id', 'Paiements')
total_paid = fields.Float('Total payé', compute='_compute_total_paid', store=True)
balance_due = fields.Float('Solde dû', compute='_compute_balance_due', store=True)

deposit_required = fields.Float('Acompte requis (%)', default=30.0)
deposit_amount = fields.Float('Montant acompte', compute='_compute_deposit_amount')

@api.depends('total_price', 'deposit_required')
def _compute_deposit_amount(self):
    for rec in self:
        rec.deposit_amount = rec.total_price * (rec.deposit_required / 100)

@api.depends('payment_ids.amount')
def _compute_total_paid(self):
    for rec in self:
        rec.total_paid = sum(p.amount for p in rec.payment_ids)

@api.depends('total_price', 'total_paid')
def _compute_balance_due(self):
    for rec in self:
        rec.balance_due = rec.total_price - rec.total_paid

def action_register_payment(self):
    """Ouvrir wizard pour enregistrer un paiement"""
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'travel.payment.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_reservation_id': self.id,
            'default_amount': self.balance_due,
        }
    }
```

---

### 5️⃣ PRIORITÉ MOYENNE : Gestion des Commissions

**Ajouter un modèle de commission** :

```python
class TravelCommission(models.Model):
    _name = 'travel.commission'
    _description = 'Commission Fournisseur'
    
    reservation_id = fields.Many2one('travel.reservation', 'Réservation', required=True)
    supplier_id = fields.Many2one('res.partner', 'Fournisseur', required=True)
    
    commission_type = fields.Selection([
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe')
    ], 'Type', default='percentage', required=True)
    
    commission_rate = fields.Float('Taux (%)')
    commission_amount = fields.Float('Montant', compute='_compute_commission', store=True)
    
    base_amount = fields.Float('Montant de base')
    
    status = fields.Selection([
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('paid', 'Payé')
    ], 'Statut', default='pending')
    
    invoice_id = fields.Many2one('account.move', 'Facture fournisseur')
    
    @api.depends('commission_type', 'commission_rate', 'base_amount')
    def _compute_commission(self):
        for rec in self:
            if rec.commission_type == 'percentage':
                rec.commission_amount = rec.base_amount * (rec.commission_rate / 100)
            else:
                rec.commission_amount = rec.commission_rate
```

---

### 6️⃣ PRIORITÉ MOYENNE : Rapports et Statistiques

**Ajouter des vues de reporting** :

```python
class TravelReservationReport(models.Model):
    _name = 'travel.reservation.report'
    _description = 'Rapport Réservations'
    _auto = False
    _order = 'date desc'
    
    date = fields.Date('Date', readonly=True)
    member_id = fields.Many2one('travel.member', 'Client', readonly=True)
    destination_id = fields.Many2one('travel.destination', 'Destination', readonly=True)
    
    total_reservations = fields.Integer('Nb Réservations', readonly=True)
    total_revenue = fields.Float('CA Total', readonly=True)
    total_cost = fields.Float('Coût Total', readonly=True)
    total_margin = fields.Float('Marge', readonly=True)
    margin_percent = fields.Float('Marge (%)', readonly=True)
    
    avg_sale_price = fields.Float('Prix moyen vente', readonly=True)
    total_participants = fields.Integer('Total Pax', readonly=True)
    
    status = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé')
    ], 'Statut', readonly=True)
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () as id,
                    DATE(r.create_date) as date,
                    r.member_id,
                    r.destination_id,
                    r.status,
                    COUNT(r.id) as total_reservations,
                    SUM(r.total_price) as total_revenue,
                    SUM(r.purchase_amount * r.nights) as total_cost,
                    SUM(r.total_price - (r.purchase_amount * r.nights)) as total_margin,
                    CASE 
                        WHEN SUM(r.total_price) > 0 
                        THEN ((SUM(r.total_price) - SUM(r.purchase_amount * r.nights)) / SUM(r.total_price) * 100)
                        ELSE 0 
                    END as margin_percent,
                    AVG(r.sale_amount) as avg_sale_price,
                    SUM(r.participants) as total_participants
                FROM travel_reservation r
                GROUP BY DATE(r.create_date), r.member_id, r.destination_id, r.status
            )
        """ % self._table)
```

---

### 7️⃣ PRIORITÉ BASSE : Notifications Automatiques

**Ajouter un système de notifications** :

```python
class TravelReservation(models.Model):
    _inherit = 'travel.reservation'
    
    def _send_notification(self, template_name, recipients):
        """Envoyer une notification email"""
        template = self.env.ref(f'travel_pro.{template_name}')
        if template:
            for recipient in recipients:
                template.send_mail(
                    self.id,
                    force_send=True,
                    email_values={'email_to': recipient}
                )
    
    def action_confirm_reservation(self):
        res = super().action_confirm_reservation()
        # Notifier le client
        if self.member_id.email:
            self._send_notification(
                'email_reservation_confirmed',
                [self.member_id.email]
            )
        return res
    
    @api.model
    def _cron_send_reminders(self):
        """Envoyer des rappels avant le voyage"""
        today = fields.Date.today()
        reminder_date = today + timedelta(days=7)
        
        upcoming_reservations = self.search([
            ('check_in', '=', reminder_date),
            ('status', '=', 'confirmed')
        ])
        
        for reservation in upcoming_reservations:
            if reservation.member_id.email:
                reservation._send_notification(
                    'email_travel_reminder',
                    [reservation.member_id.email]
                )
```

---

### 8️⃣ PRIORITÉ BASSE : Amélioration de l'Interface

**Dashboard avec graphiques** :

```xml
<!-- views/dashboard.xml -->
<record id="view_travel_dashboard" model="ir.ui.view">
    <field name="name">travel.dashboard</field>
    <field name="model">travel.reservation</field>
    <field name="arch" type="xml">
        <dashboard>
            <view type="graph">
                <graph string="Réservations par mois" type="line">
                    <field name="check_in" type="row" interval="month"/>
                    <field name="total_price" type="measure"/>
                </graph>
            </view>
            <group>
                <group col="2">
                    <aggregate name="total_revenue" field="total_price" 
                              group_operator="sum" string="CA Total"/>
                    <aggregate name="avg_price" field="total_price" 
                              group_operator="avg" string="Ticket Moyen"/>
                </group>
                <group col="2">
                    <aggregate name="count" field="id" 
                              string="Nb Réservations"/>
                    <aggregate name="total_pax" field="participants" 
                              group_operator="sum" string="Total Passagers"/>
                </group>
            </group>
        </dashboard>
    </field>
</record>
```

**Vue Kanban pour les réservations** :

```xml
<record id="view_reservation_kanban" model="ir.ui.view">
    <field name="name">reservation.kanban</field>
    <field name="model">travel.reservation</field>
    <field name="arch" type="xml">
        <kanban default_group_by="status" class="o_kanban_mobile">
            <field name="name"/>
            <field name="member_id"/>
            <field name="destination_id"/>
            <field name="check_in"/>
            <field name="total_price"/>
            <field name="status"/>
            <templates>
                <t t-name="kanban-box">
                    <div class="oe_kanban_card oe_kanban_global_click">
                        <div class="o_kanban_card_header">
                            <div class="o_kanban_card_header_title">
                                <div class="o_primary"><field name="name"/></div>
                                <div class="o_secondary"><field name="member_id"/></div>
                            </div>
                        </div>
                        <div class="o_kanban_card_content">
                            <div><i class="fa fa-map-marker"/> <field name="destination_id"/></div>
                            <div><i class="fa fa-calendar"/> <field name="check_in"/></div>
                            <div><i class="fa fa-money"/> <field name="total_price" widget="monetary"/></div>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

---

### 9️⃣ PRIORITÉ BASSE : Intégration API

**Connecter des APIs de réservation** :

```python
class TravelReservation(models.Model):
    _inherit = 'travel.reservation'
    
    def _call_booking_api(self, api_provider):
        """Appeler une API de réservation externe"""
        if api_provider == 'amadeus':
            return self._amadeus_api_call()
        elif api_provider == 'sabre':
            return self._sabre_api_call()
        elif api_provider == 'booking':
            return self._booking_api_call()
    
    def _amadeus_api_call(self):
        """Intégration Amadeus API"""
        import requests
        
        url = "https://api.amadeus.com/v2/shopping/hotel-offers"
        headers = {
            'Authorization': f'Bearer {self._get_amadeus_token()}'
        }
        params = {
            'cityCode': self.destination_id.city_code,
            'checkInDate': self.check_in,
            'checkOutDate': self.check_out,
            'adults': self.adults,
            'roomQuantity': 1
        }
        
        response = requests.get(url, headers=headers, params=params)
        return response.json()
```

---

## 🔐 Amélioration de la Sécurité

### Créer des Groupes Utilisateurs

```xml
<!-- security/travel_security.xml -->
<odoo>
    <record id="group_travel_agent" model="res.groups">
        <field name="name">Agent de Voyage</field>
        <field name="category_id" ref="base.module_category_sales"/>
    </record>
    
    <record id="group_travel_manager" model="res.groups">
        <field name="name">Manager Agence</field>
        <field name="category_id" ref="base.module_category_sales"/>
        <field name="implied_ids" eval="[(4, ref('group_travel_agent'))]"/>
    </record>
    
    <record id="group_travel_director" model="res.groups">
        <field name="name">Directeur Agence</field>
        <field name="category_id" ref="base.module_category_sales"/>
        <field name="implied_ids" eval="[(4, ref('group_travel_manager'))]"/>
    </record>
</odoo>
```

### Règles d'Enregistrement

```xml
<!-- security/travel_rules.xml -->
<odoo>
    <!-- Agent : voir uniquement ses propres réservations -->
    <record id="rule_reservation_agent" model="ir.rule">
        <field name="name">Agent : Réservations personnelles</field>
        <field name="model_id" ref="model_travel_reservation"/>
        <field name="groups" eval="[(4, ref('group_travel_agent'))]"/>
        <field name="domain_force">[('create_uid', '=', user.id)]</field>
    </record>
    
    <!-- Manager : voir toutes les réservations -->
    <record id="rule_reservation_manager" model="ir.rule">
        <field name="name">Manager : Toutes réservations</field>
        <field name="model_id" ref="model_travel_reservation"/>
        <field name="groups" eval="[(4, ref('group_travel_manager'))]"/>
        <field name="domain_force">[(1, '=', 1)]</field>
    </record>
</odoo>
```

---

## 📱 Amélioration Mobile

**Vue Mobile Optimisée** :

```xml
<record id="view_reservation_mobile" model="ir.ui.view">
    <field name="name">reservation.mobile</field>
    <field name="model">travel.reservation</field>
    <field name="arch" type="xml">
        <form string="Réservation" class="o_form_mobile">
            <sheet>
                <div class="oe_title">
                    <h1><field name="name"/></h1>
                </div>
                <group>
                    <field name="member_id"/>
                    <field name="destination_id"/>
                    <field name="check_in"/>
                    <field name="check_out"/>
                    <field name="total_price" widget="monetary"/>
                    <field name="status" widget="badge"/>
                </group>
                <footer>
                    <button name="action_create_sale_order" type="object" 
                            string="Créer Devis" class="btn-primary"/>
                </footer>
            </sheet>
        </form>
    </field>
</record>
```

---

## 🔄 Plan de Migration

### Phase 1 (Semaine 1-2) : Fondations
1. ✅ Ajouter workflow d'approbation
2. ✅ Créer groupes utilisateurs
3. ✅ Améliorer sécurité

### Phase 2 (Semaine 3-4) : Fonctionnalités Core
1. ✅ Ajouter gestion vols
2. ✅ Ajouter gestion passagers
3. ✅ Ajouter paiements partiels

### Phase 3 (Semaine 5-6) : Modules Avancés
1. ✅ Gestion documentaire
2. ✅ Gestion commissions
3. ✅ Rapports et tableaux de bord

### Phase 4 (Semaine 7-8) : Optimisation
1. ✅ Notifications automatiques
2. ✅ Tests et corrections
3. ✅ Documentation utilisateur

---

## 📚 Checklist de Vérification

### Avant Déploiement
- [ ] Tests unitaires sur tous les modèles
- [ ] Vérification des contraintes SQL
- [ ] Test des workflows complets
- [ ] Vérification des droits d'accès
- [ ] Test des calculs de prix et commissions
- [ ] Test des notifications
- [ ] Backup de la base de données
- [ ] Documentation technique complète

### Après Déploiement
- [ ] Formation des utilisateurs
- [ ] Monitoring des performances
- [ ] Collecte des feedbacks
- [ ] Corrections rapides
- [ ] Plan d'amélioration continue

---

## 🎓 Ressources Utiles

### Documentation Odoo
- [Odoo Development](https://www.odoo.com/documentation/16.0/developer.html)
- [ORM API](https://www.odoo.com/documentation/16.0/developer/reference/backend/orm.html)
- [Security](https://www.odoo.com/documentation/16.0/developer/reference/backend/security.html)

### APIs de Réservation
- [Amadeus API](https://developers.amadeus.com/)
- [Sabre API](https://developer.sabre.com/)
- [Booking.com API](https://developers.booking.com/)

---

## 💡 Conclusion

Votre module TravelPro a une **excellente base**. Les améliorations proposées le transformeront en une **solution complète et professionnelle** pour les agences de voyage.

### Prochaines Étapes Recommandées
1. **Commencer par le workflow d'approbation** (impact immédiat)
2. **Ajouter la gestion des vols** (fonctionnalité clé)
3. **Implémenter les paiements partiels** (améliore le cash flow)
4. **Créer les rapports** (aide à la décision)

Bonne chance avec votre projet ! 🚀
