from odoo import models, fields

class Company(models.Model):
    _name = 'travel.company'
    _description = 'Société ou Association'

    name = fields.Char(string='Nom de la société', required=True)
    member_ids = fields.One2many('travel.member', 'company_id', string='Membres')
    
    # Nouveaux champs
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Adresse')
    website = fields.Char(string='Site Web')
