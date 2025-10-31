from odoo import models, fields, api

class TravelMember(models.Model):
    _name = 'travel.member'
    _description = 'Membre / Client'

    name = fields.Char('Nom', required=True)
    company_id = fields.Many2one('travel.company', string='Société')
    email = fields.Char('Email')
    phone = fields.Char('Téléphone')
    reservation_ids = fields.One2many('travel.reservation', 'member_id', string='Réservations')

    # PARTENAIRE AUTOMATIQUE
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')

    @api.model
    def create(self, vals):
        # Crée un contact si pas fourni
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
        # Met à jour le contact si nom/email change
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