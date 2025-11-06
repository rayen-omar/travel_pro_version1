from odoo import models, fields

class TravelCompany(models.Model):
    _name = 'travel.company'
    _description = 'Travel Company'

    name = fields.Char('Nom', required=True)
    phone = fields.Char('Téléphone')
    mobile = fields.Char('Mobile')
    email = fields.Char('Email')
    address = fields.Text('Adresse')
    website = fields.Char('Site Web')
    vat = fields.Char('Matricule Fiscal (MF)', help='Numéro d\'identification fiscale')
    member_ids = fields.One2many('travel.member', 'company_id', string='Membres')

    def action_create_member(self):
        return {
            'name': 'Créer Membre',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.member',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_company_id': self.id},
        }