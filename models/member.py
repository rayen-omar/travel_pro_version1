from odoo import models, fields

class Member(models.Model):
    _name = 'travel.member'
    _description = 'Membre de la société'

    name = fields.Char(string='Nom du membre', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Téléphone')
    company_id = fields.Many2one(
        'travel.company', 
        string='Société', 
        default=lambda self: self.env.context.get('default_company_id')
    )
    reservation_ids = fields.One2many('travel.reservation', 'member_id', string='Réservations')
