from odoo import models, fields

class TravelDestination(models.Model):
    _name = 'travel.destination'
    _description = 'Travel Destination'

    name = fields.Char('Nom', required=True)
    description = fields.Text('Description')
    price = fields.Float('Prix')
    start_date = fields.Date('Date Début')
    end_date = fields.Date('Date Fin')
    service_ids = fields.Many2many('travel.service', string='Services')
    reservation_ids = fields.One2many('travel.reservation', 'destination_id', string='Réservations')

    def action_create_reservation(self):
        """Ouvre le formulaire réservation avec voyage pré-rempli"""
        return {
            'name': 'Réserver ce Voyage',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.reservation',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_destination_id': self.id},
        }