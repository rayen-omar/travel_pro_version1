from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    reservation_id = fields.Many2one('travel.reservation', string='Réservation')
    member_id = fields.Many2one('travel.member', string='Client', related='reservation_id.member_id', store=True)
    reservation_name = fields.Char(string='Réf Réservation', related='reservation_id.name', store=True)