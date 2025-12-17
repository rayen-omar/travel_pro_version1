from odoo import api, fields, models


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

    @api.model_create_multi
    def create(self, vals_list):
        """Créer l'historique et recalculer le solde crédit du membre."""
        records = super().create(vals_list)
        
        # Récupérer tous les membres concernés
        member_ids = set(record.member_id.id for record in records if record.member_id)
        
        # Recalculer le solde pour chaque membre
        for member_id in member_ids:
            member = self.env['travel.member'].browse(member_id)
            if member.exists():
                member._compute_credit_balance()
                member.flush_recordset(['credit_balance'])
        
        return records

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