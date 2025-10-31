# models/member.py
from odoo import models, fields, api

class TravelMember(models.Model):
    _name = 'travel.member'
    _description = 'Membre / Client'

    name = fields.Char('Nom', required=True)
    company_id = fields.Many2one('travel.company', string='Société')
    email = fields.Char('Email')
    phone = fields.Char('Téléphone')
    reservation_ids = fields.One2many('travel.reservation', 'member_id', string='Réservations')
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')

    # === SYSTÈME DE CRÉDIT ===
    credit_balance = fields.Float('Solde Crédit', compute='_compute_credit_balance', store=True, readonly=True)
    credit_history_ids = fields.One2many('travel.credit.history', 'member_id', string='Historique Crédit')

    @api.depends('credit_history_ids.amount')
    def _compute_credit_balance(self):
        for rec in self:
            rec.credit_balance = sum(h.amount for h in rec.credit_history_ids)

    @api.model
    def create(self, vals):
        if not vals.get('partner_id'):
            partner = self.env['res.partner'].create({
                'name': vals.get('name', 'Client'),
                'email': vals.get('email'),
                'phone': vals.get('phone'),
                'customer_rank': 1,
            })
            vals['partner_id'] = partner.id
        return super().create(vals)

    def write(self, vals):
        for rec in self:
            if 'name' in vals or 'email' in vals or 'phone' in vals:
                rec.partner_id.write({
                    'name': vals.get('name', rec.name),
                    'email': vals.get('email', rec.email),
                    'phone': vals.get('phone', rec.phone),
                })
        return super().write(vals)

    def action_create_reservation(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'travel.reservation',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_member_id': self.id},
        }

    # === RECHARGER CRÉDIT ===
    def action_recharge_credit(self):
        return {
            'name': 'Recharger Crédit',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.credit.recharge',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_member_id': self.id},
        }