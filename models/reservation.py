from odoo import api, fields, models
from odoo.exceptions import UserError


class TravelReservation(models.Model):
    _name = 'travel.reservation'
    _description = 'Réservation Voyage'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Référence', default='Nouveau', readonly=True)
    member_id = fields.Many2one('travel.member', string='Client', required=True)
    destination_id = fields.Many2one('travel.destination', string='Destination', required=True)
    
    # Type de voyage
    trip_type = fields.Selection([
        ('hotel', 'Hôtel'),
        ('voyage_organise', 'Voyage Organisé'),
        ('billetrie', 'Billetrie'),
        ('autre', 'Autre')
    ], string='Type de Voyage', required=True, default='hotel', tracking=True)
    
    check_in = fields.Date('Check In', required=True)
    check_out = fields.Date('Check Out', required=True)
    nights = fields.Integer('Nuitées', compute='_compute_nights', store=True)
    adults = fields.Integer('Adultes', default=1)
    children = fields.Integer('Enfants', default=0)
    infants = fields.Integer('Bébés', default=0)
    participants = fields.Integer('Total Pax', compute='_compute_participants', store=True)
    hotel_service_id = fields.Many2one('travel.service', string='Hôtel', domain="[('type', '=', 'hebergement')]")
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', domain="[('supplier_rank', '>', 0)]")
    local_or_foreign = fields.Selection([('local', 'Local'), ('foreign', 'Étranger')], string='Type', default='local')
    room_category = fields.Selection([('standard', 'Standard'), ('ls', 'LS'), ('autre', 'Autre')], string='Chambre', required=True, default='standard')
    room_type = fields.Selection([('single', 'Simple'), ('double', 'Double'), ('triple', 'Triple')], string='Type', required=True, default='double')
    
    # Prix du voyage (prix total pour toutes les nuits - TTC)
    price = fields.Float('Prix du Voyage (Total TTC TND)', digits=(16, 2), help="Prix total TTC du voyage pour toutes les nuits en TND (rempli automatiquement depuis le voyage sélectionné)")
    
    # Prix d'achat (peut être rempli manuellement ou calculé automatiquement depuis le fournisseur)
    purchase_amount = fields.Float('Prix Achat (TND)', digits=(16, 2),
                                   help="Prix d'achat en TND (peut être rempli manuellement ou calculé automatiquement depuis les services du fournisseur)")
    
    # Total calculé
    total_price = fields.Float('Total (TND)', digits=(16, 2), compute='_compute_total', store=True, 
                               help="Total en TND = Prix du Voyage + Services additionnels")
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id, 
                                  required=True)
    service_ids = fields.Many2many('travel.service', string='Services')
    sale_order_id = fields.Many2one('sale.order', string='Devis', readonly=True)
    invoice_ids = fields.One2many('account.move', 'reservation_id', string='Factures')
    invoice_count = fields.Integer(string='Nombre de Factures', compute='_compute_invoice_count')
    cash_operation_ids = fields.One2many('cash.register.operation', 'reservation_id', string='Opérations Caisse')
    cash_operation_count = fields.Integer(string='Opérations Caisse', compute='_compute_cash_operation_count')
    pos_order_ids = fields.One2many('pos.order', 'reservation_id', string='Commandes POS')
    pos_order_count = fields.Integer(string='Commandes POS', compute='_compute_pos_order_count')
    
    status = fields.Selection([
        ('draft', 'Brouillon'), ('confirmed', 'Confirmé'), ('done', 'Terminé'), ('cancel', 'Annulé')
    ], default='draft', tracking=True)

    use_credit = fields.Boolean('Utiliser crédit')
    credit_used = fields.Float('Crédit utilisé (TND)', digits=(16, 2), compute='_compute_credit_used', store=True)
    remaining_to_pay = fields.Float('Reste à payer (TND)', digits=(16, 2), compute='_compute_remaining', store=True)
    
    # Champs calculés pour workflow (sans store pour éviter les problèmes de migration)
    has_sale_order = fields.Boolean(string='A un Devis', compute='_compute_workflow_status', store=False)
    has_invoice = fields.Boolean(string='A une Facture', compute='_compute_workflow_status', store=False)
    has_payment = fields.Boolean(string='A un Paiement', compute='_compute_workflow_status', store=False)
    workflow_progress = fields.Selection([
        ('0', '0% - Brouillon'),
        ('25', '25% - Devis créé'),
        ('50', '50% - Facturé'),
        ('75', '75% - Partiellement payé'),
        ('100', '100% - Payé'),
    ], string='Progression', compute='_compute_workflow_status', store=False)
    workflow_progress_percent = fields.Integer(
        string='Progression (%)',
        compute='_compute_workflow_status',
        store=False,
        help='Pourcentage de progression du workflow (0-100) pour le widget progressbar'
    )

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

    def action_compute_purchase_amount(self):
        """Action pour calculer automatiquement le prix d'achat depuis les services du fournisseur"""
        self.ensure_one()
        if self.supplier_id and self.supplier_id.travel_service_ids:
            self.purchase_amount = sum(service.price for service in self.supplier_id.travel_service_ids if service.price)
        else:
            self.purchase_amount = 0.0
        return True

    @api.depends('nights', 'price', 'service_ids.price')
    def _compute_total(self):
        for rec in self:
            # Calculer le total : prix du voyage + services additionnels
            base_price = rec.price or 0.0
            
            # Ajouter les services additionnels (ceux qui ne sont pas dans destination.service_ids)
            services_price = sum(s.price for s in rec.service_ids if s.price)
            rec.total_price = base_price + services_price

    @api.depends('use_credit', 'member_id.credit_balance', 'total_price')
    def _compute_credit_used(self):
        for rec in self:
            if rec.use_credit and rec.member_id.credit_balance > 0:
                rec.credit_used = min(rec.member_id.credit_balance, rec.total_price)
            else:
                rec.credit_used = 0

    @api.depends('total_price', 'credit_used')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining_to_pay = rec.total_price - rec.credit_used

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        """Calculer le nombre de factures."""
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends('cash_operation_ids')
    def _compute_cash_operation_count(self):
        """Calculer le nombre d'opérations de caisse."""
        for rec in self:
            rec.cash_operation_count = len(rec.cash_operation_ids.filtered(lambda o: o.state == 'confirmed'))

    @api.depends('pos_order_ids')
    def _compute_pos_order_count(self):
        """Calculer le nombre de commandes POS."""
        for rec in self:
            rec.pos_order_count = len(rec.pos_order_ids.filtered(lambda o: o.state in ['paid', 'done', 'invoiced']))

    @api.depends('sale_order_id', 'invoice_ids', 'cash_operation_ids', 'pos_order_ids', 'remaining_to_pay', 'status')
    def _compute_workflow_status(self):
        """Calculer l'état du workflow et la progression."""
        for rec in self:
            # Utiliser sudo() pour éviter les problèmes de cache
            rec.has_sale_order = bool(rec.sale_order_id)
            rec.has_invoice = bool(rec.invoice_ids)
            
            # Calculer les paiements (caisse + POS)
            total_paid = 0.0
            if rec.cash_operation_ids:
                receipts = rec.cash_operation_ids.filtered(
                    lambda o: o.type == 'receipt' and o.state == 'confirmed'
                )
                total_paid += sum(receipts.mapped('amount'))
            
            if rec.pos_order_ids:
                paid_orders = rec.pos_order_ids.filtered(
                    lambda o: o.state in ['paid', 'done', 'invoiced']
                )
                total_paid += sum(paid_orders.mapped('amount_total'))
            
            rec.has_payment = total_paid > 0
            
            # Calculer la progression
            if rec.status == 'cancel':
                rec.workflow_progress = '0'
                rec.workflow_progress_percent = 0
            elif not rec.has_sale_order:
                rec.workflow_progress = '0'
                rec.workflow_progress_percent = 0
            elif not rec.has_invoice:
                rec.workflow_progress = '25'
                rec.workflow_progress_percent = 25
            elif not rec.has_payment:
                rec.workflow_progress = '50'
                rec.workflow_progress_percent = 50
            elif rec.remaining_to_pay and rec.remaining_to_pay > 0.01:
                rec.workflow_progress = '75'
                rec.workflow_progress_percent = 75
            else:
                rec.workflow_progress = '100'
                rec.workflow_progress_percent = 100

    def action_create_sale_order(self):
        """Créer un devis n'est plus nécessaire - vous pouvez facturer directement."""
        self.ensure_one()
        
        # Mettre à jour le statut pour confirmer la réservation
        if self.status == 'draft':
            self.status = 'confirmed'
        
        # Afficher un message informatif
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Devis non nécessaire',
                'message': 'Vous pouvez facturer directement cette réservation sans créer de devis. Utilisez le bouton "Facturer".',
                'type': 'info',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window_close',
                }
            }
        }

    def action_print_quote(self):
        """Imprimer le devis de réservation."""
        self.ensure_one()
        return self.env.ref('travel_pro_version1.action_report_reservation_quote').report_action(self)

    def action_view_sale_order(self):
        """Voir le résumé de la réservation au lieu du devis."""
        self.ensure_one()
        
        # Retourner simplement la vue formulaire de la réservation
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Devis non utilisé',
                'message': 'Le système de devis n\'est plus utilisé. Vous pouvez voir toutes les informations dans cette réservation et facturer directement.',
                'type': 'info',
                'sticky': False,
            }
        }

    @api.onchange('destination_id')
    def _onchange_destination_id(self):
        """Remplir automatiquement les informations depuis le voyage sélectionné"""
        if self.destination_id:
            # Remplir les dates depuis le voyage
            if self.destination_id.start_date:
                self.check_in = self.destination_id.start_date
            if self.destination_id.end_date:
                self.check_out = self.destination_id.end_date
            
            # Remplir le prix depuis le voyage (prix total pour toutes les nuits)
            if self.destination_id.price:
                self.price = self.destination_id.price
            
            # Remplir les services depuis le voyage (optionnel)
            if self.destination_id.service_ids:
                self.service_ids = [(6, 0, self.destination_id.service_ids.ids)]

    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        """Marquer automatiquement le partenaire comme fournisseur et proposer de calculer le prix d'achat"""
        if self.supplier_id and self.supplier_id.supplier_rank == 0:
            self.supplier_id.supplier_rank = 1
        # Calculer automatiquement le prix d'achat si le fournisseur a des services (optionnel)
        if self.supplier_id and self.supplier_id.travel_service_ids:
            # Somme des prix de tous les services du fournisseur
            self.purchase_amount = sum(service.price for service in self.supplier_id.travel_service_ids if service.price)
        elif not self.purchase_amount:
            # Ne réinitialiser que si le montant est vide
            self.purchase_amount = 0.0

    def write(self, vals):
        """Mettre à jour supplier_rank lors de la sauvegarde"""
        result = super().write(vals)
        if 'supplier_id' in vals and vals['supplier_id']:
            supplier = self.env['res.partner'].browse(vals['supplier_id'])
            if supplier.supplier_rank == 0:
                supplier.supplier_rank = 1
        return result

    @api.model
    def create(self, vals):
        """Créer la réservation et marquer le fournisseur si nécessaire"""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('travel.reservation') or 'Nouveau'
        record = super().create(vals)
        if record.supplier_id and record.supplier_id.supplier_rank == 0:
            record.supplier_id.supplier_rank = 1
        return record

    def action_create_purchase(self):
        self.ensure_one()
        if not self.supplier_id:
            raise UserError("Fournisseur requis.")
        po = self.env['purchase.order'].create_from_reservation(self)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_invoice(self):
        """Créer une facture client Travel depuis la réservation."""
        self.ensure_one()
        
        # Vérifier que le membre a une société associée
        if not self.member_id:
            raise UserError("Le membre est requis pour créer une facture.")
        
        if not self.member_id.company_id:
            raise UserError("Le membre doit avoir une société associée pour créer une facture.")
        
        # Créer la facture client Travel
        invoice_vals = {
            'travel_company_id': self.member_id.company_id.id,
            'member_ids': [(6, 0, [self.member_id.id])],
            'date_invoice': fields.Date.context_today(self),
        }
        
        invoice = self.env['travel.invoice.client'].create(invoice_vals)
        
        # Créer les lignes de facture depuis la réservation
        line_vals = {
            'invoice_id': invoice.id,
            'passenger_id': self.member_id.id,
            'reference': f"R-{str(self.id).zfill(5)}",
            'description': f"Réservation {self.name or 'N/A'} - {self.destination_id.name if self.destination_id else ''}",
            'destination_id': self.destination_id.id if self.destination_id else False,
            'reservation_id': self.id,
            'quantity': 1.0,
            'price_ttc': self.total_price,  # Le prix de la réservation est TTC
            'tax_rate': '7',  # Par défaut 7%, peut être modifié
        }
        
        self.env['travel.invoice.client.line'].create(line_vals)
        
        # Mettre à jour le statut si nécessaire
        if self.status == 'confirmed':
            self.status = 'done'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'travel.invoice.client',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoices(self):
        """Voir toutes les factures de la réservation."""
        self.ensure_one()
        
        # Rechercher les factures travel.invoice.client qui contiennent cette réservation
        invoice_lines = self.env['travel.invoice.client.line'].search([
            ('reservation_id', '=', self.id)
        ])
        invoice_ids = invoice_lines.mapped('invoice_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Factures',
            'res_model': 'travel.invoice.client',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoice_ids)],
            'context': {},
        }

    def action_view_cash_operations(self):
        """Voir toutes les opérations de caisse de la réservation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Opérations de Caisse',
            'res_model': 'cash.register.operation',
            'view_mode': 'tree,form',
            'domain': [('reservation_id', '=', self.id)],
            'context': {'default_reservation_id': self.id, 'default_type': 'receipt'},
        }

    def action_view_pos_orders(self):
        """Voir toutes les commandes POS de la réservation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commandes POS',
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'domain': [('reservation_id', '=', self.id)],
            'context': {'default_reservation_id': self.id},
        }

    def action_open_pos(self):
        """Enregistrer un paiement en caisse pour la réservation"""
        self.ensure_one()
        if self.remaining_to_pay <= 0:
            raise UserError("Rien à payer pour cette réservation.")
        
        if not self.member_id.partner_id:
            raise UserError("Le membre doit avoir un partenaire associé.")
        
        # Créer directement une opération de caisse (reçu)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enregistrer un Paiement',
            'res_model': 'cash.register.operation',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_type': 'receipt',
                'default_reservation_id': self.id,
                'default_partner_id': self.member_id.partner_id.id,
                'default_amount': self.remaining_to_pay,
                'default_description': f'Paiement pour {self.name} - {self.destination_id.name if self.destination_id else ""}',
            },
        }

    def action_cancel_and_credit(self):
        self.ensure_one()
        if self.status in ['done', 'cancel']:
            return
        if self.total_price > 0:
            self.env['travel.credit.history'].create({
                'member_id': self.member_id.id,
                'amount': self.total_price,
                'type': 'refund',
                'reservation_id': self.id,
            })
        self.status = 'cancel'

    def action_confirm(self):
        self.write({'status': 'confirmed'})

    def action_done(self):
        self.write({'status': 'done'})

    def action_cancel(self):
        self.write({'status': 'cancel'})