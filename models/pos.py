from odoo import models, fields

class PosOrder(models.Model):
    _inherit = 'pos.order'

    reservation_id = fields.Many2one('travel.reservation', string='Réservation')
    member_id = fields.Many2one('travel.member', string='Client')

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.reservation_id:
            vals.update({
                'reservation_id': self.reservation_id.id,
                'partner_id': self.reservation_id.member_id.partner_id.id,
            })
        return vals