from odoo import api, fields, models
from odoo.exceptions import UserError


class TravelReservation(models.Model):
    _name = 'travel.reservation'
    _description = 'Réservation Voyage'

    name = fields.Char('Référence', default='Nouveau', readonly=True)
    member_id = fields.Many2one('travel.member', string='Client', required=True)
    company_id = fields.Many2one('travel.company', string='Société', related='member_id.company_id', store=True, readonly=True)
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
    
    # Date de création de la réservation
    create_date = fields.Datetime('Date de Création', readonly=True, index=True)

    use_credit = fields.Boolean('Utiliser crédit')
    credit_used = fields.Float('Crédit utilisé (TND)', digits=(16, 2), compute='_compute_credit_used', store=True)
    remaining_to_pay = fields.Float('Reste à payer (TND)', digits=(16, 2), compute='_compute_remaining', store=True)
    

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
        """Confirmer la réservation et déduire le crédit si utilisé."""
        for rec in self:
            # Vérifier si le crédit a déjà été débité pour cette réservation
            existing_credit = self.env['travel.credit.history'].search([
                ('reservation_id', '=', rec.id),
                ('type', '=', 'usage')
            ], limit=1)
            
            # Si le crédit est utilisé et n'a pas encore été débité
            if rec.use_credit and rec.credit_used > 0 and not existing_credit:
                # Vérifier que le client a suffisamment de crédit
                if rec.member_id.credit_balance < rec.credit_used:
                    raise UserError(
                        f"Le client {rec.member_id.name} n'a pas suffisamment de crédit.\n"
                        f"Crédit disponible: {rec.member_id.credit_balance:.2f} TND\n"
                        f"Crédit requis: {rec.credit_used:.2f} TND"
                    )
                
                # Créer l'enregistrement d'utilisation du crédit (montant négatif pour déduire)
                credit_history = self.env['travel.credit.history'].create({
                    'member_id': rec.member_id.id,
                    'amount': -rec.credit_used,  # Montant négatif pour déduire
                    'type': 'usage',
                    'reservation_id': rec.id,
                    'note': f'Utilisation crédit pour réservation {rec.name}',
                })
                
                # Forcer le flush pour s'assurer que l'historique est sauvegardé
                credit_history.flush_recordset()
                rec.member_id.flush_recordset(['credit_history_ids'])
                
                # Invalider et forcer le recalcul du solde crédit
                rec.member_id.invalidate_recordset(['credit_balance', 'credit_history_ids'])
                
                # Recharger le membre pour forcer le recalcul du champ stocké
                rec.member_id._compute_credit_balance()
                rec.member_id.flush_recordset(['credit_balance'])
            
            rec.write({'status': 'confirmed'})

    def action_done(self):
        self.write({'status': 'done'})

    def action_cancel(self):
        """Annuler la réservation et rembourser le crédit utilisé si la réservation était confirmée."""
        for rec in self:
            # Si la réservation était confirmée et avait utilisé du crédit, le rembourser
            if rec.status == 'confirmed' and rec.use_credit and rec.credit_used > 0:
                # Vérifier s'il y a un historique d'utilisation de crédit pour cette réservation
                credit_usage = self.env['travel.credit.history'].search([
                    ('reservation_id', '=', rec.id),
                    ('type', '=', 'usage')
                ], limit=1)
                
                # Si le crédit a été débité, le rembourser
                if credit_usage:
                    credit_refund = self.env['travel.credit.history'].create({
                        'member_id': rec.member_id.id,
                        'amount': rec.credit_used,  # Montant positif pour rembourser
                        'type': 'refund',
                        'reservation_id': rec.id,
                        'note': f'Remboursement crédit pour annulation réservation {rec.name}',
                    })
                    
                    # Forcer le flush pour s'assurer que l'historique est sauvegardé
                    credit_refund.flush_recordset()
                    rec.member_id.flush_recordset(['credit_history_ids'])
                    
                    # Invalider et forcer le recalcul du solde crédit
                    rec.member_id.invalidate_recordset(['credit_balance', 'credit_history_ids'])
                    
                    # Recharger le membre pour forcer le recalcul du champ stocké
                    rec.member_id._compute_credit_balance()
                    rec.member_id.flush_recordset(['credit_balance'])
            
            rec.write({'status': 'cancel'})