from odoo import api, fields, models
from odoo.osv import expression


class TravelCompany(models.Model):
    _name = 'travel.company'
    _description = 'Travel Company'

    name = fields.Char('Nom', required=True)
    phone = fields.Char('Téléphone')
    mobile = fields.Char('Mobile')
    email = fields.Char('Email')
    address = fields.Text('Adresse')
    website = fields.Char('Site Web')
    vat = fields.Char('Matricule Fiscale', help='Numéro d\'identification fiscale')
    member_ids = fields.One2many('travel.member', 'company_id', string='Membres')

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """Recherche par nom et matricule fiscale"""
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('vat', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, order=order)

    def action_create_member(self):
        return {
            'name': 'Créer Membre',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.member',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_company_id': self.id},
        }