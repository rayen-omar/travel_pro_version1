from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Reservation(models.Model):
    _name = 'travel.reservation'
    _description = 'Réservation voyage'
    _rec_name = 'name'

    name = fields.Char(string='Référence', copy=False, readonly=True)
    member_id = fields.Many2one('travel.member', string='Membre', required=True)
    destination_id = fields.Many2one('travel.destination', string='Voyage', required=True)
    participants = fields.Integer(string='Nombre de participants', default=1)
    adults = fields.Integer(string='Adultes', default=1)
    children = fields.Integer(string='Enfants', default=0)
    infants = fields.Integer(string='Bébés', default=0)

    # Hotel-specific
    hotel_service_id = fields.Many2one('travel.service', string='Hôtel',
                                       domain="[('type','in',('hebergement'))]",
                                       help='Sélectionner un service de type hébergement')
    check_in = fields.Date(string='Check In')
    check_out = fields.Date(string='Check Out')
    nights = fields.Integer(string='Nombre de nuit(s)', compute='_compute_nights', store=True)
    room_type = fields.Selection([
        ('single','Logement simple (LS)'),
        ('double','Chambre double'),
        ('triple','Triple'),
        ('suite','Suite'),
    ], string='Type de chambre')
    supplier_id = fields.Many2one('res.partner', string='Fournisseur',
                                  help='Fournisseur lié à la réservation (optionnel)')
    local_or_foreign = fields.Selection([('local','Local'), ('foreign','Étranger')], string='Local ou étranger', default='local')
    service_ids = fields.Many2many('travel.service', string='Services sélectionnés')
    purchase_amount = fields.Monetary(string='Montant Achat', help='Montant d\'achat total (fournisseur)')
    sale_amount = fields.Monetary(string='Montant Vente', help='Montant de vente personnalisé (override)')
    total_price = fields.Monetary(string='Prix total', compute='_compute_total', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    status = fields.Selection([
        ('pending','En attente'),
        ('confirmed','Confirmé'),
        ('cancelled','Annulé')
    ], string='Statut', default='pending')
    sale_order_id = fields.Many2one('sale.order', string='Devis')

    @api.model
    def create(self, vals):
        # auto-generate a reference using ir.sequence if present
        seq_code = 'travel.reservation'
        seq = self.env['ir.sequence'].sudo().search([('code','=', seq_code)], limit=1)
        if seq:
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code(seq_code)
        return super(Reservation, self).create(vals)

    @api.onchange('hotel_service_id')
    def _onchange_hotel_service(self):
        # copier automatiquement le supplier_id depuis le service hôtelier
        if self.hotel_service_id and self.hotel_service_id.supplier_id:
            self.supplier_id = self.hotel_service_id.supplier_id

    @api.depends('check_in','check_out')
    def _compute_nights(self):
        for rec in self:
            rec.nights = 0
            if rec.check_in and rec.check_out:
                delta = (rec.check_out - rec.check_in).days
                rec.nights = delta if delta > 0 else 0

    @api.depends('participants','destination_id.price','service_ids','hotel_service_id','nights','sale_amount')
    def _compute_total(self):
        for rec in self:
            total = 0.0
            base_price = rec.destination_id.price or 0.0
            total += (rec.participants or 0) * base_price

            if rec.hotel_service_id and rec.nights:
                room_price = rec.hotel_service_id.room_price or 0.0
                total += room_price * rec.nights

            total += sum((s.price or 0.0) for s in rec.service_ids)

            if rec.sale_amount and rec.sale_amount > 0.0:
                rec.total_price = rec.sale_amount
            else:
                rec.total_price = total

    @api.constrains('check_in','check_out')
    def _check_dates(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_in >= rec.check_out:
                raise ValidationError("La date de départ (Check In) doit être antérieure à la date de retour (Check Out).")

    def create_sale_order(self):
        SaleOrder = self.env['sale.order'].sudo()
        SaleOrderLine = self.env['sale.order.line'].sudo()
        Product = self.env['product.product'].sudo()
        currency = self.currency_id or self.env.company.currency_id

        for rec in self:
            # partner: on recherche un partner existant par nom (ou créer)
            partner = False
            if rec.member_id and rec.member_id.name:
                partner = self.env['res.partner'].sudo().search([('name','=', rec.member_id.name)], limit=1)
            if not partner and rec.member_id:
                partner = self.env['res.partner'].sudo().create({'name': rec.member_id.name})

            order_vals = {
                'partner_id': partner.id if partner else False,
                'currency_id': currency.id,
                'client_order_ref': rec.name or False,
            }
            order = SaleOrder.create(order_vals)

            # Ligne voyage
            product_voyage = Product.search([('name','ilike','Voyage')], limit=1)
            if not product_voyage:
                product_voyage = Product.create({'name': 'Voyage', 'list_price': rec.destination_id.price or 0.0, 'type': 'service'})
            SaleOrderLine.create({
                'order_id': order.id,
                'product_id': product_voyage.id,
                'product_uom_qty': rec.participants or 1,
                'price_unit': rec.destination_id.price or 0.0,
            })

            # Ligne hébergement (par nuit)
            if rec.hotel_service_id and rec.nights:
                product_hotel = Product.search([('name','ilike', rec.hotel_service_id.name)], limit=1)
                if not product_hotel:
                    product_hotel = Product.create({'name': rec.hotel_service_id.name, 'list_price': rec.hotel_service_id.room_price or 0.0, 'type': 'service'})
                SaleOrderLine.create({
                    'order_id': order.id,
                    'product_id': product_hotel.id,
                    'product_uom_qty': rec.nights,
                    'price_unit': rec.hotel_service_id.room_price or 0.0,
                })

            # Autres services (one-time)
            for srv in rec.service_ids:
                product_srv = Product.search([('name','ilike', srv.name)], limit=1)
                if not product_srv:
                    product_srv = Product.create({'name': srv.name, 'list_price': srv.price or 0.0, 'type': 'service'})
                SaleOrderLine.create({
                    'order_id': order.id,
                    'product_id': product_srv.id,
                    'product_uom_qty': 1,
                    'price_unit': srv.price or 0.0,
                })

            rec.sale_order_id = order.id
            rec.status = 'confirmed'
