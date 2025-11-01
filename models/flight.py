from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TravelFlight(models.Model):
    _name = 'travel.flight'
    _description = 'Vol'
    _order = 'departure_date'
    
    # ========== INFORMATIONS DE BASE ==========
    name = fields.Char('Référence', compute='_compute_name', store=True)
    reservation_id = fields.Many2one('travel.reservation', string='Réservation', required=True, ondelete='cascade')
    
    flight_type = fields.Selection([
        ('oneway', 'Aller Simple'),
        ('roundtrip', 'Aller-Retour'),
        ('multi', 'Multi-destinations')
    ], string='Type de Vol', required=True, default='roundtrip')
    
    # ========== VOL ALLER ==========
    departure_city = fields.Char('Ville Départ', required=True)
    departure_airport = fields.Char('Aéroport Départ')
    arrival_city = fields.Char('Ville Arrivée', required=True)
    arrival_airport = fields.Char('Aéroport Arrivée')
    
    departure_date = fields.Datetime('Date/Heure Départ', required=True)
    arrival_date = fields.Datetime('Date/Heure Arrivée', required=True)
    
    flight_number = fields.Char('Numéro de Vol', required=True)
    airline_id = fields.Many2one('res.partner', string='Compagnie Aérienne', 
                                  domain="[('is_company', '=', True)]")
    airline_code = fields.Char('Code IATA')
    
    # ========== VOL RETOUR ==========
    has_return = fields.Boolean('Vol Retour', compute='_compute_has_return', store=True)
    
    return_departure_date = fields.Datetime('Date/Heure Départ Retour')
    return_arrival_date = fields.Datetime('Date/Heure Arrivée Retour')
    return_flight_number = fields.Char('Numéro Vol Retour')
    return_airline_id = fields.Many2one('res.partner', string='Compagnie Retour',
                                        domain="[('is_company', '=', True)]")
    
    # ========== INFORMATIONS VOL ==========
    class_type = fields.Selection([
        ('economy', 'Économique'),
        ('premium_economy', 'Premium Économique'),
        ('business', 'Affaires'),
        ('first', 'Première Classe')
    ], string='Classe', required=True, default='economy')
    
    cabin_baggage = fields.Char('Bagage Cabine', default='1 x 10kg')
    checked_baggage = fields.Char('Bagage Soute', default='1 x 23kg')
    
    booking_reference = fields.Char('PNR / Référence Réservation')
    ticket_number = fields.Char('Numéro Billet')
    
    # ========== DURÉE ==========
    duration = fields.Float('Durée Vol (heures)', compute='_compute_duration', store=True)
    return_duration = fields.Float('Durée Retour (heures)', compute='_compute_duration', store=True)
    
    # ========== TARIFS ==========
    purchase_price = fields.Float('Prix Achat', required=True, digits='Product Price')
    sale_price = fields.Float('Prix Vente', required=True, digits='Product Price')
    
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                   default=lambda self: self.env.company.currency_id)
    
    taxes_included = fields.Boolean('Taxes Incluses', default=True)
    tax_amount = fields.Float('Montant Taxes', digits='Product Price')
    
    margin = fields.Float('Marge', compute='_compute_margin', store=True)
    margin_percent = fields.Float('Marge (%)', compute='_compute_margin', store=True)
    
    # ========== PASSAGERS ==========
    passenger_ids = fields.Many2many('travel.passenger', 'flight_passenger_rel', 
                                     'flight_id', 'passenger_id', string='Passagers')
    passenger_count = fields.Integer('Nombre Passagers', compute='_compute_passenger_count', store=True)
    
    # ========== STATUT ==========
    status = fields.Selection([
        ('quote', 'Devis'),
        ('booked', 'Réservé'),
        ('ticketed', 'Billeté'),
        ('cancelled', 'Annulé')
    ], string='Statut', default='quote', tracking=True)
    
    # ========== FOURNISSEUR ==========
    supplier_id = fields.Many2one('res.partner', string='Fournisseur/GDS',
                                   domain="[('supplier_rank', '>', 0)]")
    supplier_reference = fields.Char('Référence Fournisseur')
    
    # ========== NOTES ==========
    note = fields.Text('Notes')
    special_services = fields.Text('Services Spéciaux')
    
    # ========== CONTRAINTES ==========
    _sql_constraints = [
        ('check_dates', 'CHECK(arrival_date > departure_date)', 
         'La date d\'arrivée doit être après le départ !'),
        ('check_prices', 'CHECK(sale_price >= purchase_price)', 
         'Le prix de vente doit être supérieur ou égal au prix d\'achat !'),
    ]
    
    # ========== COMPUTED FIELDS ==========
    
    @api.depends('flight_number', 'departure_city', 'arrival_city')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.flight_number} - {rec.departure_city} → {rec.arrival_city}"
    
    @api.depends('flight_type')
    def _compute_has_return(self):
        for rec in self:
            rec.has_return = rec.flight_type == 'roundtrip'
    
    @api.depends('departure_date', 'arrival_date', 'return_departure_date', 'return_arrival_date')
    def _compute_duration(self):
        for rec in self:
            if rec.departure_date and rec.arrival_date:
                delta = rec.arrival_date - rec.departure_date
                rec.duration = delta.total_seconds() / 3600  # Convertir en heures
            else:
                rec.duration = 0
            
            if rec.return_departure_date and rec.return_arrival_date:
                delta = rec.return_arrival_date - rec.return_departure_date
                rec.return_duration = delta.total_seconds() / 3600
            else:
                rec.return_duration = 0
    
    @api.depends('sale_price', 'purchase_price')
    def _compute_margin(self):
        for rec in self:
            rec.margin = rec.sale_price - rec.purchase_price
            rec.margin_percent = (rec.margin / rec.sale_price * 100) if rec.sale_price > 0 else 0
    
    @api.depends('passenger_ids')
    def _compute_passenger_count(self):
        for rec in self:
            rec.passenger_count = len(rec.passenger_ids)
    
    # ========== VALIDATIONS ==========
    
    @api.constrains('departure_date', 'arrival_date')
    def _check_flight_dates(self):
        for rec in self:
            if rec.departure_date and rec.arrival_date:
                if rec.arrival_date <= rec.departure_date:
                    raise ValidationError("La date d'arrivée doit être après le départ !")
    
    @api.constrains('return_departure_date', 'return_arrival_date', 'arrival_date')
    def _check_return_dates(self):
        for rec in self:
            if rec.has_return and rec.return_departure_date:
                if rec.return_departure_date < rec.arrival_date:
                    raise ValidationError("Le vol retour ne peut partir avant l'arrivée du vol aller !")
                if rec.return_arrival_date and rec.return_arrival_date <= rec.return_departure_date:
                    raise ValidationError("La date d'arrivée du retour doit être après son départ !")
    
    # ========== ACTIONS ==========
    
    def action_book(self):
        """Marquer comme réservé"""
        for rec in self:
            rec.status = 'booked'
        return True
    
    def action_issue_ticket(self):
        """Émettre le billet"""
        for rec in self:
            if rec.status != 'booked':
                raise ValidationError("Le vol doit d'abord être réservé !")
            rec.status = 'ticketed'
        return True
    
    def action_cancel(self):
        """Annuler le vol"""
        for rec in self:
            rec.status = 'cancelled'
        return True
    
    def action_view_passengers(self):
        """Voir les passagers de ce vol"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Passagers',
            'res_model': 'travel.passenger',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.passenger_ids.ids)],
        }


class TravelFlightSegment(models.Model):
    """Pour les vols multi-destinations avec escales"""
    _name = 'travel.flight.segment'
    _description = 'Segment de Vol'
    _order = 'sequence, departure_date'
    
    sequence = fields.Integer('Séquence', default=10)
    flight_id = fields.Many2one('travel.flight', string='Vol', required=True, ondelete='cascade')
    
    departure_city = fields.Char('Départ', required=True)
    departure_airport = fields.Char('Aéroport Départ')
    arrival_city = fields.Char('Arrivée', required=True)
    arrival_airport = fields.Char('Aéroport Arrivée')
    
    departure_date = fields.Datetime('Date Départ', required=True)
    arrival_date = fields.Datetime('Date Arrivée', required=True)
    
    flight_number = fields.Char('N° Vol', required=True)
    airline_id = fields.Many2one('res.partner', string='Compagnie')
    
    duration = fields.Float('Durée (h)', compute='_compute_duration', store=True)
    
    @api.depends('departure_date', 'arrival_date')
    def _compute_duration(self):
        for rec in self:
            if rec.departure_date and rec.arrival_date:
                delta = rec.arrival_date - rec.departure_date
                rec.duration = delta.total_seconds() / 3600
            else:
                rec.duration = 0
