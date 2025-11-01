from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

class TravelReservation(models.Model):
    _name = 'travel.reservation'
    _description = 'Réservation Voyage'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ========== INFORMATIONS DE BASE ==========
    name = fields.Char('Référence', default='Nouveau', readonly=True, copy=False)
    member_id = fields.Many2one('travel.member', string='Client', required=True, tracking=True)
    destination_id = fields.Many2one('travel.destination', string='Destination', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)
    
    # ========== DATES ET PÉRIODES ==========
    check_in = fields.Date('Check In', required=True, tracking=True)
    check_out = fields.Date('Check Out', required=True, tracking=True)
    nights = fields.Integer('Nuitées', compute='_compute_nights', store=True)
    
    # ========== PARTICIPANTS ==========
    adults = fields.Integer('Adultes', default=1, required=True)
    children = fields.Integer('Enfants', default=0)
    infants = fields.Integer('Bébés', default=0)
    participants = fields.Integer('Total Pax', compute='_compute_participants', store=True)
    passenger_ids = fields.One2many('travel.passenger', 'reservation_id', string='Liste Passagers')
    
    # ========== HÉBERGEMENT ==========
    hotel_service_id = fields.Many2one('travel.service', string='Hôtel', 
                                       domain="[('type', '=', 'hebergement')]")
    supplier_id = fields.Many2one('res.partner', string='Fournisseur Hôtel', 
                                   domain="[('supplier_rank', '>', 0)]")
    local_or_foreign = fields.Selection([
        ('local', 'Local'), 
        ('foreign', 'Étranger')
    ], string='Type', default='local')
    
    room_category = fields.Selection([
        ('standard', 'Standard'), 
        ('ls', 'LS'), 
        ('superior', 'Supérieur'),
        ('deluxe', 'Deluxe'),
        ('suite', 'Suite')
    ], string='Catégorie Chambre', required=True, default='standard')
    
    room_type = fields.Selection([
        ('single', 'Simple'), 
        ('double', 'Double'), 
        ('triple', 'Triple'),
        ('quad', 'Quadruple'),
        ('family', 'Familiale')
    ], string='Type Chambre', required=True, default='double')
    
    # ========== VOLS ==========
    flight_ids = fields.One2many('travel.flight', 'reservation_id', string='Vols')
    has_flight = fields.Boolean('Inclut vol', compute='_compute_has_flight', store=True)
    
    # ========== TARIFS ==========
    purchase_amount = fields.Float('Prix Achat/Nuit', digits='Product Price')
    sale_amount = fields.Float('Prix Vente/Nuit', digits='Product Price')
    
    # Services supplémentaires
    service_ids = fields.Many2many('travel.service', string='Services Additionnels')
    service_total = fields.Float('Total Services', compute='_compute_service_total', store=True)
    
    # Totaux
    accommodation_subtotal = fields.Float('Sous-total Hébergement', compute='_compute_totals', store=True)
    flight_subtotal = fields.Float('Sous-total Vols', compute='_compute_totals', store=True)
    total_price = fields.Float('Prix Total', compute='_compute_totals', store=True, tracking=True)
    margin = fields.Float('Marge', compute='_compute_margin', store=True)
    margin_percent = fields.Float('Marge (%)', compute='_compute_margin', store=True)
    
    # ========== CRÉDIT CLIENT ==========
    use_credit = fields.Boolean('Utiliser crédit client')
    credit_used = fields.Float('Crédit utilisé', compute='_compute_credit_used', store=True)
    
    # ========== PAIEMENTS ==========
    payment_ids = fields.One2many('travel.payment', 'reservation_id', string='Paiements')
    total_paid = fields.Float('Total Payé', compute='_compute_payment_status', store=True)
    balance_due = fields.Float('Solde Dû', compute='_compute_payment_status', store=True, tracking=True)
    remaining_to_pay = fields.Float('Reste à Payer', compute='_compute_remaining', store=True)
    
    deposit_required = fields.Float('Acompte Requis (%)', default=30.0)
    deposit_amount = fields.Float('Montant Acompte', compute='_compute_deposit_amount', store=True)
    deposit_paid = fields.Boolean('Acompte Payé', compute='_compute_payment_status', store=True)
    
    payment_status = fields.Selection([
        ('not_paid', 'Non Payé'),
        ('partial', 'Partiellement Payé'),
        ('paid', 'Payé'),
        ('overpaid', 'Trop Payé')
    ], string='État Paiement', compute='_compute_payment_status', store=True)
    
    # ========== WORKFLOW ==========
    status = fields.Selection([
        ('draft', 'Brouillon'),
        ('pending', 'En Attente Validation'),
        ('validated', 'Validé Manager'),
        ('confirmed', 'Confirmé'),
        ('in_progress', 'En Cours'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé')
    ], string='Statut', default='draft', tracking=True, required=True)
    
    # Approbations
    submitted_user_id = fields.Many2one('res.users', string='Soumis par', readonly=True)
    submitted_date = fields.Datetime('Date Soumission', readonly=True)
    
    validated_user_id = fields.Many2one('res.users', string='Validé par', readonly=True)
    validated_date = fields.Datetime('Date Validation', readonly=True)
    
    confirmed_user_id = fields.Many2one('res.users', string='Confirmé par', readonly=True)
    confirmed_date = fields.Datetime('Date Confirmation', readonly=True)
    
    cancellation_reason = fields.Text('Motif Annulation')
    cancelled_user_id = fields.Many2one('res.users', string='Annulé par', readonly=True)
    cancelled_date = fields.Datetime('Date Annulation', readonly=True)
    
    # ========== DOCUMENTS ==========
    document_ids = fields.One2many('travel.document', 'reservation_id', string='Documents')
    document_count = fields.Integer('Nb Documents', compute='_compute_document_count')
    
    # ========== COMMISSIONS ==========
    commission_ids = fields.One2many('travel.commission', 'reservation_id', string='Commissions')
    total_commission = fields.Float('Total Commissions', compute='_compute_total_commission', store=True)
    
    # ========== LIENS VERS AUTRES MODULES ==========
    sale_order_id = fields.Many2one('sale.order', string='Commande Vente', readonly=True, copy=False)
    purchase_order_ids = fields.One2many('purchase.order', 'reservation_id', string='Commandes Achat')
    invoice_ids = fields.One2many('account.move', 'reservation_id', string='Factures')
    
    # ========== NOTES ==========
    note = fields.Text('Notes Internes')
    special_request = fields.Text('Demandes Spéciales Client')
    
    # ========== CONTRAINTES SQL ==========
    _sql_constraints = [
        ('check_dates', 'CHECK(check_out > check_in)', 
         'La date de départ doit être après la date d\'arrivée !'),
        ('check_adults', 'CHECK(adults > 0)', 
         'Il doit y avoir au moins un adulte !'),
        ('check_deposit', 'CHECK(deposit_required >= 0 AND deposit_required <= 100)', 
         'L\'acompte doit être entre 0 et 100% !'),
    ]
    
    # ========== COMPUTED FIELDS ==========
    
    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                rec.nights = (rec.check_out - rec.check_in).days
            else:
                rec.nights = 0
    
    @api.depends('adults', 'children', 'infants')
    def _compute_participants(self):
        for rec in self:
            rec.participants = rec.adults + rec.children + rec.infants
    
    @api.depends('flight_ids')
    def _compute_has_flight(self):
        for rec in self:
            rec.has_flight = len(rec.flight_ids) > 0
    
    @api.depends('service_ids.price')
    def _compute_service_total(self):
        for rec in self:
            rec.service_total = sum(s.price for s in rec.service_ids)
    
    @api.depends('nights', 'sale_amount', 'service_total', 'flight_ids.sale_price')
    def _compute_totals(self):
        for rec in self:
            rec.accommodation_subtotal = rec.nights * rec.sale_amount
            rec.flight_subtotal = sum(f.sale_price for f in rec.flight_ids)
            rec.total_price = rec.accommodation_subtotal + rec.flight_subtotal + rec.service_total
    
    @api.depends('total_price', 'nights', 'purchase_amount', 'flight_ids.purchase_price')
    def _compute_margin(self):
        for rec in self:
            total_cost = (rec.nights * rec.purchase_amount) + sum(f.purchase_price for f in rec.flight_ids)
            rec.margin = rec.total_price - total_cost
            rec.margin_percent = (rec.margin / rec.total_price * 100) if rec.total_price > 0 else 0
    
    @api.depends('total_price', 'deposit_required')
    def _compute_deposit_amount(self):
        for rec in self:
            rec.deposit_amount = rec.total_price * (rec.deposit_required / 100)
    
    @api.depends('use_credit', 'member_id.credit_balance', 'total_price')
    def _compute_credit_used(self):
        for rec in self:
            if rec.use_credit and rec.member_id.credit_balance > 0:
                rec.credit_used = min(rec.member_id.credit_balance, rec.total_price)
            else:
                rec.credit_used = 0
    
    @api.depends('payment_ids.amount', 'total_price', 'deposit_amount')
    def _compute_payment_status(self):
        for rec in self:
            rec.total_paid = sum(p.amount for p in rec.payment_ids if p.state == 'posted')
            rec.balance_due = rec.total_price - rec.total_paid
            rec.deposit_paid = rec.total_paid >= rec.deposit_amount
            
            if rec.total_paid == 0:
                rec.payment_status = 'not_paid'
            elif rec.total_paid < rec.total_price:
                rec.payment_status = 'partial'
            elif rec.total_paid == rec.total_price:
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'overpaid'
    
    @api.depends('total_price', 'credit_used', 'total_paid')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining_to_pay = rec.total_price - rec.credit_used - rec.total_paid
    
    @api.depends('document_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)
    
    @api.depends('commission_ids.commission_amount')
    def _compute_total_commission(self):
        for rec in self:
            rec.total_commission = sum(c.commission_amount for c in rec.commission_ids)
    
    # ========== VALIDATIONS ==========
    
    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                if rec.check_out <= rec.check_in:
                    raise ValidationError("La date de départ doit être après la date d'arrivée !")
    
    @api.constrains('adults', 'children', 'infants', 'passenger_ids')
    def _check_passengers(self):
        for rec in self:
            total_declared = rec.adults + rec.children + rec.infants
            total_passengers = len(rec.passenger_ids)
            if total_passengers > 0 and total_passengers != total_declared:
                raise ValidationError(
                    f"Le nombre de passagers ({total_passengers}) ne correspond pas "
                    f"au nombre déclaré ({total_declared}) !"
                )
    
    # ========== ACTIONS WORKFLOW ==========
    
    def action_submit_for_approval(self):
        """Soumettre pour validation (Agent)"""
        for rec in self:
            if rec.status != 'draft':
                raise UserError("Seules les réservations en brouillon peuvent être soumises.")
            
            rec.write({
                'status': 'pending',
                'submitted_user_id': self.env.user.id,
                'submitted_date': fields.Datetime.now()
            })
            
            # Notifier le manager
            rec._notify_managers("Nouvelle réservation à valider", 
                                f"La réservation {rec.name} nécessite votre validation.")
        
        return True
    
    def action_validate(self):
        """Valider la réservation (Manager)"""
        for rec in self:
            if rec.status != 'pending':
                raise UserError("Seules les réservations en attente peuvent être validées.")
            
            # Vérifier que l'utilisateur est manager
            if not self.env.user.has_group('travel_pro_version1.group_travel_manager'):
                raise UserError("Vous n'avez pas les droits pour valider des réservations.")
            
            rec.write({
                'status': 'validated',
                'validated_user_id': self.env.user.id,
                'validated_date': fields.Datetime.now()
            })
            
            # Notifier le directeur si montant > seuil
            if rec.total_price > 5000:
                rec._notify_directors("Réservation importante à confirmer", 
                                     f"La réservation {rec.name} de {rec.total_price}€ nécessite votre confirmation.")
        
        return True
    
    def action_confirm(self):
        """Confirmer définitivement (Director ou auto si < seuil)"""
        for rec in self:
            if rec.status not in ['validated', 'pending']:
                raise UserError("La réservation doit être validée avant confirmation.")
            
            # Si montant > 5000€, seul directeur peut confirmer
            if rec.total_price > 5000:
                if not self.env.user.has_group('travel_pro_version1.group_travel_director'):
                    raise UserError("Seul un directeur peut confirmer une réservation > 5000€.")
            
            rec.write({
                'status': 'confirmed',
                'confirmed_user_id': self.env.user.id,
                'confirmed_date': fields.Datetime.now()
            })
            
            # Créer automatiquement le devis
            rec.action_create_sale_order()
        
        return True
    
    def action_start_travel(self):
        """Marquer le voyage comme en cours"""
        for rec in self:
            if rec.status != 'confirmed':
                raise UserError("La réservation doit être confirmée.")
            rec.status = 'in_progress'
        return True
    
    def action_complete(self):
        """Marquer le voyage comme terminé"""
        for rec in self:
            if rec.status != 'in_progress':
                raise UserError("Le voyage doit être en cours.")
            if rec.balance_due > 0:
                raise UserError("Le solde doit être réglé avant de clôturer.")
            rec.status = 'done'
        return True
    
    def action_cancel(self):
        """Annuler la réservation"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Annuler la réservation',
            'res_model': 'travel.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id}
        }
    
    def action_reset_to_draft(self):
        """Remettre en brouillon (Admin uniquement)"""
        for rec in self:
            if not self.env.user.has_group('base.group_system'):
                raise UserError("Seul un administrateur peut remettre en brouillon.")
            rec.status = 'draft'
        return True
    
    # ========== ACTIONS MÉTIER ==========
    
    def action_create_sale_order(self):
        """Créer le devis de vente"""
        self.ensure_one()
        
        if self.sale_order_id:
            return self.action_view_sale_order()
        
        # Créer produit générique si n'existe pas
        product = self.env['product.product'].search([
            ('type', '=', 'service'),
            ('name', '=', 'Service Voyage')
        ], limit=1)
        
        if not product:
            product = self.env['product.product'].create({
                'name': 'Service Voyage',
                'type': 'service',
                'list_price': 0,
            })
        
        # Créer commande
        order_vals = {
            'partner_id': self.member_id.partner_id.id,
            'date_order': fields.Datetime.now(),
        }
        order = self.env['sale.order'].create(order_vals)
        
        # Lignes de commande
        lines = []
        
        # Hébergement
        if self.accommodation_subtotal > 0:
            lines.append((0, 0, {
                'product_id': product.id,
                'name': f"{self.hotel_service_id.name or 'Hébergement'} - {self.nights} nuit(s)",
                'product_uom_qty': 1,
                'price_unit': self.accommodation_subtotal,
            }))
        
        # Vols
        for flight in self.flight_ids:
            lines.append((0, 0, {
                'product_id': product.id,
                'name': f"Vol {flight.departure_city} → {flight.arrival_city}",
                'product_uom_qty': 1,
                'price_unit': flight.sale_price,
            }))
        
        # Services
        for service in self.service_ids:
            lines.append((0, 0, {
                'product_id': product.id,
                'name': service.name,
                'product_uom_qty': 1,
                'price_unit': service.price,
            }))
        
        order.write({'order_line': lines})
        self.sale_order_id = order.id
        
        # Appliquer crédit si demandé
        if self.use_credit and self.credit_used > 0:
            self.env['travel.credit.history'].create({
                'member_id': self.member_id.id,
                'amount': -self.credit_used,
                'type': 'usage',
                'reservation_id': self.id,
                'note': f'Crédit utilisé pour réservation {self.name}'
            })
        
        return self.action_view_sale_order()
    
    def action_view_sale_order(self):
        """Voir le devis"""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("Aucun devis associé. Créez-le d'abord.")
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_purchase(self):
        """Créer commande(s) d'achat fournisseur"""
        self.ensure_one()
        
        if not self.supplier_id:
            raise UserError("Veuillez sélectionner un fournisseur d'hébergement.")
        
        # Créer PO pour l'hébergement
        product = self.env['product.product'].search([
            ('type', '=', 'service')
        ], limit=1)
        
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier_id.id,
            'reservation_id': self.id,
        })
        
        self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': product.id,
            'name': f"Hébergement {self.destination_id.name} - {self.nights} nuits",
            'product_qty': 1,
            'price_unit': self.nights * self.purchase_amount,
            'date_planned': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_register_payment(self):
        """Enregistrer un paiement"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enregistrer un paiement',
            'res_model': 'travel.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reservation_id': self.id,
                'default_amount': self.balance_due,
            }
        }
    
    def action_view_documents(self):
        """Voir les documents"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'travel.document',
            'view_mode': 'tree,form',
            'domain': [('reservation_id', '=', self.id)],
            'context': {'default_reservation_id': self.id}
        }
    
    # ========== NOTIFICATIONS ==========
    
    def _notify_managers(self, subject, body):
        """Notifier tous les managers"""
        managers = self.env.ref('travel_pro_version1.group_travel_manager').users
        for manager in managers:
            self.message_post(
                body=body,
                subject=subject,
                partner_ids=[manager.partner_id.id],
                message_type='notification'
            )
    
    def _notify_directors(self, subject, body):
        """Notifier tous les directeurs"""
        directors = self.env.ref('travel_pro_version1.group_travel_director').users
        for director in directors:
            self.message_post(
                body=body,
                subject=subject,
                partner_ids=[director.partner_id.id],
                message_type='notification'
            )
    
    # ========== CRON JOBS ==========
    
    @api.model
    def _cron_send_reminders(self):
        """Rappel automatique 7 jours avant le départ"""
        reminder_date = fields.Date.today() + timedelta(days=7)
        
        reservations = self.search([
            ('check_in', '=', reminder_date),
            ('status', '=', 'confirmed')
        ])
        
        for reservation in reservations:
            if reservation.member_id.email:
                # Envoyer email de rappel
                template = self.env.ref('travel_pro_version1.email_travel_reminder', raise_if_not_found=False)
                if template:
                    template.send_mail(reservation.id, force_send=True)
    
    @api.model
    def _cron_auto_complete_travels(self):
        """Marquer automatiquement comme terminé après check-out"""
        yesterday = fields.Date.today() - timedelta(days=1)
        
        reservations = self.search([
            ('check_out', '=', yesterday),
            ('status', '=', 'in_progress')
        ])
        
        for reservation in reservations:
            if reservation.balance_due <= 0:
                reservation.status = 'done'
    
    # ========== OVERRIDES ==========
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('travel.reservation') or 'RES/000'
        return super().create(vals)
    
    def write(self, vals):
        # Empêcher modification si confirmé (sauf admin)
        if not self.env.user.has_group('base.group_system'):
            if any(rec.status in ['confirmed', 'done'] for rec in self):
                protected_fields = ['member_id', 'check_in', 'check_out', 'total_price']
                if any(f in vals for f in protected_fields):
                    raise UserError("Impossible de modifier une réservation confirmée.")
        
        return super().write(vals)
    
    def unlink(self):
        # Empêcher suppression si pas en brouillon
        for rec in self:
            if rec.status != 'draft':
                raise UserError(f"Impossible de supprimer la réservation {rec.name} (statut: {rec.status}).")
        return super().unlink()
