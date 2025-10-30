from odoo import models, fields

class Travel(models.Model):
    _name = 'travel.destination'
    _description = 'Voyage'

    name = fields.Char(string='Nom du voyage', required=True)
    description = fields.Text(string='Description')
    price = fields.Float(string='Prix par participant')
    start_date = fields.Date(string='Date de départ')
    end_date = fields.Date(string='Date de retour')
    service_ids = fields.One2many('travel.service', 'destination_id', string='Services')
    reservation_ids = fields.One2many('travel.reservation', 'destination_id', string='Réservations')
