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
    
    # Prix du voyage (prix total pour toutes les nuits)
    price = fields.Float('Prix du Voyage (Total TND)', digits=(16, 2), help="Prix total du voyage pour toutes les nuits en TND (rempli automatiquement depuis le voyage sélectionné)")
    
    # Prix d'achat (calculé automatiquement depuis le fournisseur)
    purchase_amount = fields.Float('Prix Achat (TND)', digits=(16, 2), compute='_compute_purchase_amount', store=True,
                                   help="Somme des prix des services du fournisseur choisi en TND (rempli automatiquement)")
    
    # Total calculé
    total_price = fields.Float('Total (TND)', digits=(16, 2), compute='_compute_total', store=True, 
                               help="Total en TND = Prix du Voyage + Services additionnels")
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id, 
                                  required=True)
    service_ids = fields.Many2many('travel.service', string='Services')
    sale_order_id = fields.Many2one('sale.order', string='Devis', readonly=True)
    status = fields.Selection([
        ('draft', 'Brouillon'), ('confirmed', 'Confirmé'), ('done', 'Terminé'), ('cancel', 'Annulé')
    ], default='draft', tracking=True)

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

    @api.depends('supplier_id', 'supplier_id.travel_service_ids', 'supplier_id.travel_service_ids.price')
    def _compute_purchase_amount(self):
        """Calculer le prix d'achat depuis la somme des prix des services du fournisseur"""
        for rec in self:
            if rec.supplier_id and rec.supplier_id.travel_service_ids:
                # Somme des prix de tous les services du fournisseur
                rec.purchase_amount = sum(service.price for service in rec.supplier_id.travel_service_ids if service.price)
            else:
                rec.purchase_amount = 0.0

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

    def action_create_sale_order(self):
        self.ensure_one()
        product = self.env['product.product'].search([('type', '=', 'service')], limit=1)
        if not product:
            product = self.env['product.product'].create({'name': 'Service', 'type': 'service'})

        if not self.sale_order_id:
            order = self.env['sale.order'].create({
                'partner_id': self.member_id.partner_id.id,
            })
            self.sale_order_id = order.id
            self.status = 'confirmed'

        lines = [(5, 0, 0)]
        if self.hotel_service_id:
            # Utiliser price (prix total du voyage)
            price_unit = self.price or 0.0
            lines.append((0, 0, {
                'product_id': product.id,
                'name': f"{self.hotel_service_id.name} - {self.nights} nuits",
                'product_uom_qty': 1,
                'price_unit': price_unit,
            }))
        for s in self.service_ids:
            lines.append((0, 0, {
                'product_id': product.id,
                'name': s.name,
                'product_uom_qty': 1,
                'price_unit': s.price,
            }))
        self.sale_order_id.write({'order_line': lines})

        if self.use_credit and self.credit_used > 0:
            self.env['travel.credit.history'].create({
                'member_id': self.member_id.id,
                'amount': -self.credit_used,
                'type': 'usage',
                'reservation_id': self.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("Aucun devis associé.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
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
        """Marquer automatiquement le partenaire comme fournisseur"""
        if self.supplier_id and self.supplier_id.supplier_rank == 0:
            self.supplier_id.supplier_rank = 1

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
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("Créez un devis d'abord.")
        invoices = self.sale_order_id._create_invoices()
        if invoices:
            invoices[0].write({'reservation_id': self.id})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoices[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    def action_open_pos(self):
        """Ouvrir le POS pour payer la réservation"""
        self.ensure_one()
        if self.remaining_to_pay <= 0:
            raise UserError("Rien à payer pour cette réservation.")
        
        if not self.member_id.partner_id:
            raise UserError("Le membre doit avoir un partenaire associé pour utiliser le POS.")
        
        config = self.env.ref('travel_pro_version1.pos_config_travel', raise_if_not_found=False)
        if not config:
            raise UserError("Configuration POS non trouvée. Veuillez configurer le Point de Vente.")
        
        # Vérifier s'il y a une session ouverte
        session = self.env['pos.session'].search([
            ('config_id', '=', config.id),
            ('state', '=', 'opened')
        ], limit=1)
        
        if not session:
            raise UserError("Aucune session POS ouverte. Veuillez ouvrir une session de caisse d'abord.")
        
        # Retourner l'action pour ouvrir le POS
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web#action=point_of_sale.action_client_pos_menu&config_id={config.id}',
            'target': 'self',
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