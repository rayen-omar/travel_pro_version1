from odoo import api, fields, models


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
    price = fields.Float(string='Prix (TND)', digits=(16, 2))
    room_price = fields.Float(string='Prix par nuit (TND, si hébergement)', digits=(16, 2))
    supplier_id = fields.Many2one('res.partner', string='Fournisseur')
    destination_id = fields.Many2one('travel.destination', string='Voyage')
    note = fields.Text(string='Note')

    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        """Marquer automatiquement le partenaire comme fournisseur"""
        if self.supplier_id and self.supplier_id.supplier_rank == 0:
            self.supplier_id.supplier_rank = 1

    def write(self, vals):
        """Mettre à jour supplier_rank lors de la sauvegarde"""
        result = super().write(vals)
        if 'supplier_id' in vals and vals['supplier_id']:
            supplier = self.env['res.partner'].browse(vals['supplier_id'])
            if supplier.supplier_rank == 0:
                supplier.supplier_rank = 1
        return result

    @api.model
    def create(self, vals):
        """Créer et marquer le fournisseur si nécessaire"""
        record = super().create(vals)
        if record.supplier_id and record.supplier_id.supplier_rank == 0:
            record.supplier_id.supplier_rank = 1
        return record

    def name_get(self):
        result = []
        for rec in self:
            name = rec.name
            if rec.supplier_id:
                name = f"{name} / {rec.supplier_id.name}"
            result.append((rec.id, name))
        return result