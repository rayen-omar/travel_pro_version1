from odoo import models, fields, api
from odoo.exceptions import UserError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    reservation_id = fields.Many2one('travel.reservation', string='Réservation', tracking=True)
    member_id = fields.Many2one('travel.member', string='Client Membre', tracking=True)
    destination_id = fields.Many2one('travel.destination', string='Destination', related='reservation_id.destination_id', readonly=True, store=True)

    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        """Remplir automatiquement les informations depuis la réservation"""
        if self.reservation_id:
            self.member_id = self.reservation_id.member_id.id
            if self.reservation_id.member_id.partner_id:
                self.partner_id = self.reservation_id.member_id.partner_id.id

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Remplir le partenaire depuis le membre"""
        if self.member_id and self.member_id.partner_id:
            self.partner_id = self.member_id.partner_id.id

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.reservation_id:
            vals.update({
                'reservation_id': self.reservation_id.id,
                'partner_id': self.reservation_id.member_id.partner_id.id if self.reservation_id.member_id.partner_id else self.partner_id.id,
            })
        return vals

    def action_pos_order_paid(self):
        """Mettre à jour la réservation après paiement"""
        result = super().action_pos_order_paid()
        for order in self:
            if order.reservation_id:
                # Mettre à jour le statut de la réservation si nécessaire
                if order.reservation_id.status == 'draft':
                    order.reservation_id.status = 'confirmed'
                # Créer un enregistrement de paiement pour la réservation
                # (si le modèle travel.payment existe)
        return result