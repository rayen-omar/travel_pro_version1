from odoo import models, fields, api

class TravelCreditHistory(models.Model):
    _name = 'travel.credit.history'
    _description = 'Historique Crédit Membre'
    _order = 'date desc'

    member_id = fields.Many2one('travel.member', 'Membre', required=True, ondelete='cascade')
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    amount = fields.Float('Montant (TND)', required=True, digits=(16, 2))
    type = fields.Selection([
        ('recharge', 'Recharge manuelle'),
        ('refund', 'Remboursement annulation'),
        ('usage', 'Utilisation réservation')
    ], 'Type', required=True)
    reservation_id = fields.Many2one('travel.reservation', 'Réservation')
    note = fields.Text('Note')

class TravelCreditRecharge(models.TransientModel):
    _name = 'travel.credit.recharge'
    _description = 'Recharger Crédit Membre'

    member_id = fields.Many2one('travel.member', 'Membre', required=True)
    amount = fields.Float('Montant à ajouter (TND)', required=True, digits=(16, 2))

    def action_recharge(self):
        self.env['travel.credit.history'].create({
            'member_id': self.member_id.id,
            'amount': self.amount,
            'type': 'recharge',
            'note': f'Recharge manuelle de {self.amount} TND',
        })
        return {'type': 'ir.actions.act_window_close'}