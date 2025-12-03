# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    reservation_id = fields.Many2one('travel.reservation', string='Réservation', tracking=True)
    member_id = fields.Many2one('travel.member', string='Client', related='reservation_id.member_id', store=True)
    reservation_name = fields.Char(string='Réf Réservation', related='reservation_id.name', store=True)
    
    # Champs calculés pour navigation
    cash_operation_count = fields.Integer(
        string='Opérations Caisse',
        compute='_compute_cash_operation_count'
    )

    @api.depends('reservation_id', 'reservation_id.cash_operation_ids')
    def _compute_cash_operation_count(self):
        """Calculer le nombre d'opérations de caisse liées."""
        for invoice in self:
            if invoice.reservation_id:
                operations = invoice.reservation_id.cash_operation_ids.filtered(
                    lambda o: o.invoice_id.id == invoice.id and o.state == 'confirmed'
                )
                invoice.cash_operation_count = len(operations)
            else:
                invoice.cash_operation_count = 0

    def action_view_cash_operations(self):
        """Voir les opérations de caisse liées à cette facture."""
        self.ensure_one()
        if not self.reservation_id:
            return {'type': 'ir.actions.act_window_close'}
        
        operations = self.reservation_id.cash_operation_ids.filtered(
            lambda o: o.invoice_id.id == self.id
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Opérations de Caisse',
            'res_model': 'cash.register.operation',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', operations.ids)],
            'context': {
                'default_invoice_id': self.id,
                'default_reservation_id': self.reservation_id.id,
                'default_type': 'receipt',
            },
        }