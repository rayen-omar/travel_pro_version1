from odoo import api, fields, models


class TravelDestination(models.Model):
    _name = 'travel.destination'
    _description = 'Travel Destination'

    name = fields.Char('Nom', required=True, tracking=True)
    description = fields.Text('Description')
    price = fields.Float('Prix (TND)', digits=(16, 2), tracking=True)
    start_date = fields.Date('Date Début', tracking=True)
    end_date = fields.Date('Date Fin', tracking=True)
    service_ids = fields.Many2many('travel.service', string='Services')
    reservation_ids = fields.One2many('travel.reservation', 'destination_id', string='Réservations')
    reservation_count = fields.Integer('Nombre de Réservations', compute='_compute_reservation_count')

    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        for rec in self:
            rec.reservation_count = len(rec.reservation_ids)

    def action_create_reservation(self):
        return {
            'name': 'Réserver ce Voyage',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.reservation',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_destination_id': self.id},
        }