from odoo import api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    reservation_id = fields.Many2one('travel.reservation', string='Réservation liée')
    member_id = fields.Many2one('travel.member', string='Client', related='reservation_id.member_id', store=True)

    @api.model
    def create_from_reservation(self, reservation):
        """Crée un bon de commande à partir d'une réservation"""
        if not reservation.supplier_id:
            raise UserError("Sélectionnez un fournisseur")
        product = self.env['product.product'].search([('type', '=', 'service')], limit=1)
        if not product:
            product = self.env['product.product'].create({'name': 'Service', 'type': 'service'})
        
        hotel_name = reservation.hotel_service_id.name if reservation.hotel_service_id else 'Hébergement'
        return self.create({
            'partner_id': reservation.supplier_id.id,
            'reservation_id': reservation.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': f"{hotel_name} - {reservation.nights} nuits",
                'product_qty': 1,
                'price_unit': reservation.purchase_amount if reservation.purchase_amount > 0 else (reservation.price or 0.0),
            })]
        })