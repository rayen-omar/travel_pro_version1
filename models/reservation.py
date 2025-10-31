# models/reservation.py
from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError

class TravelReservation(models.Model):
    _name = 'travel.reservation'
    _description = 'Réservation Voyage'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Référence', default='Nouveau', readonly=True)
    member_id = fields.Many2one('travel.member', string='Client', required=True)
    destination_id = fields.Many2one('travel.destination', string='Destination', required=True)
    check_in = fields.Date('Check In', required=True)
    check_out = fields.Date('Check Out', required=True)
    nights = fields.Integer('Nombre de nuitée(s)', compute='_compute_nights', store=True, readonly=True)
    adults = fields.Integer('Adultes', default=1)
    children = fields.Integer('Enfants', default=0)
    infants = fields.Integer('Bébés', default=0)
    participants = fields.Integer('Total Pax', compute='_compute_participants', store=True)
    hotel_service_id = fields.Many2one('travel.service', string='Hôtel', domain="[('type', '=', 'hebergement')]")
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', domain="[('supplier_rank', '>', 0)]")
    local_or_foreign = fields.Selection([('local', 'Hôtel local'), ('foreign', 'Hôtel étranger')], string='Local ou étranger', required=True, default='local')
    room_category = fields.Selection([('standard', 'Chambre Standard'), ('ls', 'Logement simple (LS)'), ('autre', 'Autre')], string='Chambre N°1', required=True)
    room_type = fields.Selection([('single', 'Simple'), ('double', 'Double'), ('triple', 'Triple')], string='Type de logement', required=True)
    purchase_amount = fields.Float('Montant Achat')
    sale_amount = fields.Float('Montant Vente')
    total_price = fields.Float('Total', compute='_compute_total', store=True)
    service_ids = fields.Many2many('travel.service', string='Services additionnels')
    sale_order_id = fields.Many2one('sale.order', string='Devis', readonly=True, copy=False)
    status = fields.Selection([
        ('draft', 'Brouillon'), ('confirmed', 'Confirmé'), ('done', 'Terminé'), ('cancel', 'Annulé')
    ], default='draft', tracking=True)

    # === CRÉDIT MEMBRE ===
    use_credit = fields.Boolean('Utiliser mon crédit disponible')
    credit_used = fields.Float('Crédit utilisé', compute='_compute_credit_used', store=True)
    remaining_to_pay = fields.Float('Reste à payer', compute='_compute_remaining', store=True)

    # === CALCULS ===
    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_out >= rec.check_in:
                rec.nights = (rec.check_out - rec.check_in).days
            else:
                rec.nights = 0

    @api.depends('adults', 'children', 'infants')
    def _compute_participants(self):
        for rec in self:
            rec.participants = (rec.adults or 0) + (rec.children or 0) + (rec.infants or 0)

    @api.depends('nights', 'sale_amount', 'service_ids.price')
    def _compute_total(self):
        for rec in self:
            rec.total_price = (rec.nights * (rec.sale_amount or 0)) + sum(s.price or 0 for s in rec.service_ids)

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

    # === CRÉER DEVIS (avec crédit) ===
    def action_create_sale_order(self):
        self.ensure_one()
        product = self.env['product.product'].search([('type', '=', 'service')], limit=1)
        if not product:
            product = self.env['product.product'].create({
                'name': 'Service Voyage', 'type': 'service', 'list_price': 100, 'standard_price': 80
            })

        if not self.sale_order_id:
            order = self.env['sale.order'].create({
                'partner_id': self.member_id.partner_id.id,
                'date_order': fields.Datetime.now(),
                'validity_date': self.check_out + timedelta(days=30),
                'note': f"Réservation: {self.name}\nHôtel: {self.hotel_service_id.name}\nPax: {self.adults}A/{self.children}E/{self.infants}B",
            })
            self.sale_order_id = order.id
            self.status = 'confirmed'
        else:
            order = self.sale_order_id
            order.order_line.unlink()

        if self.hotel_service_id and self.sale_amount:
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'name': f"{self.hotel_service_id.name} - {self.room_type} ({self.nights} nuits)",
                'product_uom_qty': 1,
                'price_unit': self.nights * self.sale_amount,
            })

        for s in self.service_ids:
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'name': s.name,
                'product_uom_qty': 1,
                'price_unit': s.price or 0,
            })

        # === UTILISATION DU CRÉDIT ===
        if self.use_credit and self.credit_used > 0:
            self.env['travel.credit.history'].create({
                'member_id': self.member_id.id,
                'amount': -self.credit_used,
                'type': 'usage',
                'reservation_id': self.id,
                'note': f'Utilisé pour réservation {self.name}',
            })
            order.note += f"\nCrédit utilisé: {self.credit_used}€ (reste à payer: {self.remaining_to_pay}€)"

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("Aucun devis associé à cette réservation.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_save_reservation(self):
        self.ensure_one()
        self.message_post(body="Réservation enregistrée manuellement.")
        return True

    # === ANNULER + CRÉDITER ===
    def action_cancel_and_credit(self):
        self.ensure_one()
        if self.status in ['done', 'cancel']:
            return True

        paid_amount = self.total_price
        if paid_amount > 0:
            self.env['travel.credit.history'].create({
                'member_id': self.member_id.id,
                'amount': paid_amount,
                'type': 'refund',
                'reservation_id': self.id,
                'note': f'Remboursement annulation {self.name}',
            })
            self.message_post(body=f"Annulée & {paid_amount}€ crédités au membre !")

        self.status = 'cancel'
        return True

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            seq = self.env['ir.sequence'].sudo().next_by_code('travel.reservation')
            vals['name'] = seq or 'Nouveau'
        return super().create(vals)