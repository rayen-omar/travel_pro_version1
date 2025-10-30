from odoo import models, fields

class Service(models.Model):
    _name = 'travel.service'
    _description = 'Service pour voyage'

    name = fields.Char(string='Nom du service', required=True)
    type = fields.Selection([
        ('hebergement','Hébergement'),
        ('transport','Transport'),
        ('activite','Activité'),
        ('autre','Autre')
    ], string='Type', default='autre')
    price = fields.Float(string='Prix')  # prix par unité (par exemple prix activité)
    room_price = fields.Float(string='Prix par nuit (si hébergement)',
                              help='Prix par nuit pour ce service (utilisé pour les hôtels)')
    supplier_id = fields.Many2one('res.partner', string='Fournisseur')
    destination_id = fields.Many2one('travel.destination', string='Voyage')
    note = fields.Text(string='Note')

    # helper to display supplier in hotel selection
    def name_get(self):
        result = []
        for rec in self:
            name = rec.name
            if rec.supplier_id:
                name = '%s / %s' % (name, rec.supplier_id.name)
            result.append((rec.id, name))
        return result
