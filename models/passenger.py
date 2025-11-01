from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date

class TravelPassenger(models.Model):
    _name = 'travel.passenger'
    _description = 'Passager'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # ========== INFORMATIONS PERSONNELLES ==========
    name = fields.Char('Nom Complet', compute='_compute_name', store=True)
    
    first_name = fields.Char('Prénom', required=True, tracking=True)
    middle_name = fields.Char('Deuxième Prénom')
    last_name = fields.Char('Nom', required=True, tracking=True)
    
    title = fields.Selection([
        ('mr', 'M.'),
        ('mrs', 'Mme'),
        ('ms', 'Mlle'),
        ('dr', 'Dr'),
        ('prof', 'Prof')
    ], string='Titre', default='mr')
    
    birth_date = fields.Date('Date de Naissance', required=True, tracking=True)
    age = fields.Integer('Âge', compute='_compute_age', store=True)
    
    passenger_type = fields.Selection([
        ('adult', 'Adulte (12+)'),
        ('child', 'Enfant (2-11)'),
        ('infant', 'Bébé (0-2)')
    ], string='Type Passager', compute='_compute_passenger_type', store=True)
    
    gender = fields.Selection([
        ('male', 'Masculin'),
        ('female', 'Féminin'),
        ('other', 'Autre')
    ], string='Sexe', required=True)
    
    nationality_id = fields.Many2one('res.country', string='Nationalité', required=True)
    
    # ========== CONTACT ==========
    email = fields.Char('Email')
    phone = fields.Char('Téléphone')
    mobile = fields.Char('Mobile')
    
    # ========== ADRESSE ==========
    street = fields.Char('Rue')
    street2 = fields.Char('Rue 2')
    city = fields.Char('Ville')
    zip = fields.Char('Code Postal')
    state_id = fields.Many2one('res.country.state', string='État')
    country_id = fields.Many2one('res.country', string='Pays')
    
    # ========== DOCUMENTS ==========
    passport_number = fields.Char('N° Passeport', tracking=True)
    passport_issue_date = fields.Date('Date Émission Passeport')
    passport_expiry_date = fields.Date('Date Expiration Passeport', tracking=True)
    passport_country_id = fields.Many2one('res.country', string='Pays Émetteur Passeport')
    passport_valid = fields.Boolean('Passeport Valide', compute='_compute_passport_valid', store=True)
    
    id_card_number = fields.Char('N° Carte d\'Identité')
    id_card_expiry = fields.Date('Expiration CI')
    
    # ========== VISA ==========
    visa_required = fields.Boolean('Visa Requis')
    visa_number = fields.Char('N° Visa')
    visa_type = fields.Selection([
        ('tourist', 'Touristique'),
        ('business', 'Affaires'),
        ('transit', 'Transit'),
        ('work', 'Travail'),
        ('student', 'Étudiant')
    ], string='Type de Visa')
    visa_status = fields.Selection([
        ('not_required', 'Non Requis'),
        ('pending', 'En Cours'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé'),
        ('expired', 'Expiré')
    ], string='Statut Visa', default='not_required', tracking=True)
    visa_expiry_date = fields.Date('Date Expiration Visa')
    
    # ========== PROGRAMMES FIDÉLITÉ ==========
    frequent_flyer_programs = fields.One2many('travel.frequent.flyer', 'passenger_id', 
                                              string='Programmes de Fidélité')
    
    # ========== PRÉFÉRENCES ==========
    special_meal = fields.Selection([
        ('none', 'Aucun'),
        ('vegetarian', 'Végétarien'),
        ('vegan', 'Végétalien'),
        ('halal', 'Halal'),
        ('kosher', 'Casher'),
        ('gluten_free', 'Sans Gluten'),
        ('diabetic', 'Diabétique'),
        ('child', 'Repas Enfant')
    ], string='Repas Spécial', default='none')
    
    seat_preference = fields.Selection([
        ('window', 'Fenêtre'),
        ('aisle', 'Couloir'),
        ('no_preference', 'Aucune Préférence')
    ], string='Préférence Siège', default='no_preference')
    
    special_assistance = fields.Text('Assistance Spéciale')
    wheelchair_required = fields.Boolean('Fauteuil Roulant')
    
    medical_conditions = fields.Text('Conditions Médicales')
    allergies = fields.Text('Allergies')
    
    # ========== LIAISONS ==========
    reservation_id = fields.Many2one('travel.reservation', string='Réservation', ondelete='cascade')
    member_id = fields.Many2one('travel.member', string='Client', 
                                 related='reservation_id.member_id', store=True)
    
    flight_ids = fields.Many2many('travel.flight', 'flight_passenger_rel', 
                                  'passenger_id', 'flight_id', string='Vols')
    
    # ========== DOCUMENTS ATTACHÉS ==========
    document_ids = fields.One2many('travel.document', 'passenger_id', string='Documents')
    
    # ========== NOTES ==========
    note = fields.Text('Notes')
    
    # ========== STATUT ==========
    active = fields.Boolean('Actif', default=True)
    
    # ========== COMPUTED FIELDS ==========
    
    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_name(self):
        for rec in self:
            name_parts = [rec.first_name, rec.middle_name, rec.last_name]
            rec.name = ' '.join(filter(None, name_parts))
    
    @api.depends('birth_date')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.birth_date:
                rec.age = today.year - rec.birth_date.year - (
                    (today.month, today.day) < (rec.birth_date.month, rec.birth_date.day)
                )
            else:
                rec.age = 0
    
    @api.depends('age')
    def _compute_passenger_type(self):
        for rec in self:
            if rec.age >= 12:
                rec.passenger_type = 'adult'
            elif rec.age >= 2:
                rec.passenger_type = 'child'
            else:
                rec.passenger_type = 'infant'
    
    @api.depends('passport_expiry_date')
    def _compute_passport_valid(self):
        today = date.today()
        for rec in self:
            if rec.passport_expiry_date:
                rec.passport_valid = rec.passport_expiry_date > today
            else:
                rec.passport_valid = False
    
    # ========== VALIDATIONS ==========
    
    @api.constrains('birth_date')
    def _check_birth_date(self):
        today = date.today()
        for rec in self:
            if rec.birth_date and rec.birth_date > today:
                raise ValidationError("La date de naissance ne peut pas être dans le futur !")
    
    @api.constrains('passport_expiry_date')
    def _check_passport_validity(self):
        """Vérifier que le passeport est valide pour au moins 6 mois"""
        for rec in self:
            if rec.reservation_id and rec.passport_expiry_date:
                if rec.reservation_id.check_out:
                    # Le passeport doit être valide 6 mois après le retour
                    from datetime import timedelta
                    required_validity = rec.reservation_id.check_out + timedelta(days=180)
                    if rec.passport_expiry_date < required_validity:
                        raise ValidationError(
                            f"Le passeport de {rec.name} expire le {rec.passport_expiry_date}. "
                            f"Il doit être valide jusqu'au {required_validity} (6 mois après le retour)."
                        )
    
    @api.constrains('email')
    def _check_email(self):
        for rec in self:
            if rec.email:
                import re
                if not re.match(r"[^@]+@[^@]+\.[^@]+", rec.email):
                    raise ValidationError("Format d'email invalide !")
    
    # ========== ACTIONS ==========
    
    def action_view_documents(self):
        """Voir les documents du passager"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'travel.document',
            'view_mode': 'tree,form',
            'domain': [('passenger_id', '=', self.id)],
            'context': {'default_passenger_id': self.id}
        }
    
    def action_check_passport(self):
        """Vérifier la validité du passeport"""
        self.ensure_one()
        
        warnings = []
        today = date.today()
        
        if not self.passport_number:
            warnings.append("⚠️ Aucun numéro de passeport")
        
        if not self.passport_expiry_date:
            warnings.append("⚠️ Date d'expiration manquante")
        elif self.passport_expiry_date <= today:
            warnings.append("❌ Passeport expiré !")
        elif self.passport_expiry_date <= today + timedelta(days=180):
            warnings.append("⚠️ Passeport expire dans moins de 6 mois")
        
        if warnings:
            message = "\n".join(warnings)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Vérification Passeport',
                    'message': message,
                    'type': 'warning',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Passeport Valide',
                    'message': '✅ Le passeport est valide',
                    'type': 'success',
                    'sticky': False,
                }
            }
    
    def action_request_visa(self):
        """Demander un visa"""
        self.ensure_one()
        
        if not self.visa_required:
            raise ValidationError("Aucun visa requis pour ce passager.")
        
        self.visa_status = 'pending'
        
        # Créer une activité pour le suivi
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'Demande de visa pour {self.name}',
            note=f'Destination: {self.reservation_id.destination_id.name if self.reservation_id else "N/A"}',
        )
        
        return True


class TravelFrequentFlyer(models.Model):
    """Programme de fidélité aérien"""
    _name = 'travel.frequent.flyer'
    _description = 'Programme Fidélité Aérien'
    
    passenger_id = fields.Many2one('travel.passenger', string='Passager', required=True, ondelete='cascade')
    
    airline_id = fields.Many2one('res.partner', string='Compagnie Aérienne', required=True,
                                  domain="[('is_company', '=', True)]")
    program_name = fields.Char('Nom du Programme', required=True)
    membership_number = fields.Char('N° Membre', required=True)
    
    membership_level = fields.Selection([
        ('basic', 'Basique'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond')
    ], string='Niveau', default='basic')
    
    expiry_date = fields.Date('Date Expiration')
    
    _sql_constraints = [
        ('unique_membership', 'UNIQUE(passenger_id, airline_id, membership_number)',
         'Ce numéro de membre existe déjà pour ce passager et cette compagnie !')
    ]
