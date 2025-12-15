# -*- coding: utf-8 -*-
"""
Modèle de gestion des membres/clients pour TravelPro.

Ce module gère les membres (clients) de l'agence de voyage,
incluant leurs informations personnelles, leur solde crédit
et leurs réservations.
"""
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class TravelMember(models.Model):
    """
    Membre / Client de l'agence de voyage.
    
    Un membre peut appartenir à une société (travel.company) et
    effectuer des réservations. Il dispose d'un système de crédit
    pour payer ses réservations.
    """
    _name = 'travel.member'
    _description = 'Membre / Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ===== CONTRAINTES SQL =====
    _sql_constraints = [
        ('matricule_unique', 'UNIQUE(matricule)', 
         'Le matricule doit être unique. Ce matricule existe déjà.'),
        ('partner_unique', 'UNIQUE(partner_id)',
         'Ce contact est déjà associé à un autre membre.'),
    ]

    # ===== CHAMPS =====
    name = fields.Char(
        'Nom', 
        required=True, 
        tracking=True,
        help="Nom complet du membre"
    )
    company_id = fields.Many2one(
        'travel.company', 
        string='Société', 
        tracking=True,
        help="Société à laquelle appartient ce membre"
    )
    email = fields.Char(
        'Email',
        help="Adresse email du membre"
    )
    phone = fields.Char(
        'Téléphone',
        help="Numéro de téléphone du membre"
    )
    matricule = fields.Char(
        'Matricule', 
        tracking=True,
        help="Identifiant unique du membre (ex: MEM-00001)"
    )
    partner_id = fields.Many2one(
        'res.partner', 
        string='Contact', 
        required=True, 
        ondelete='restrict',
        help="Contact Odoo associé à ce membre (créé automatiquement)"
    )
    
    # Réservations
    reservation_ids = fields.One2many(
        'travel.reservation', 
        'member_id', 
        string='Réservations'
    )
    reservation_count = fields.Integer(
        'Nombre de Réservations', 
        compute='_compute_reservation_count'
    )
    
    # Système de crédit
    credit_balance = fields.Float(
        'Solde Crédit (TND)', 
        digits=(16, 3), 
        compute='_compute_credit_balance', 
        store=True, 
        readonly=True, 
        tracking=True,
        help="Solde actuel du crédit disponible"
    )
    credit_history_ids = fields.One2many(
        'travel.credit.history', 
        'member_id', 
        string='Historique Crédit'
    )

    # ===== VALIDATIONS =====
    # Pattern RFC 5322 simplifié pour validation email
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    @api.constrains('email')
    def _check_email_format(self):
        """Valider le format de l'email s'il est fourni."""
        for record in self:
            if record.email:
                if not self.EMAIL_PATTERN.match(record.email):
                    raise ValidationError(
                        f"Format d'email invalide: {record.email}\n"
                        "Le format attendu est: exemple@domaine.com"
                    )

    @api.constrains('phone')
    def _check_phone_format(self):
        """Valider le format du téléphone s'il est fourni."""
        for record in self:
            if record.phone:
                # Nettoyer le numéro (supprimer espaces et caractères spéciaux)
                cleaned = record.phone.replace(' ', '').replace('-', '').replace('.', '').replace('+', '')
                if len(cleaned) < 8:
                    raise ValidationError(
                        f"Numéro de téléphone trop court: {record.phone}\n"
                        "Le numéro doit contenir au moins 8 chiffres."
                    )

    # ===== COMPUTED FIELDS =====
    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        """Calculer le nombre de réservations du membre."""
        for rec in self:
            rec.reservation_count = len(rec.reservation_ids)

    @api.depends('credit_history_ids.amount')
    def _compute_credit_balance(self):
        """Calculer le solde crédit depuis l'historique."""
        for rec in self:
            rec.credit_balance = sum(h.amount for h in rec.credit_history_ids)

    # ===== CRUD METHODS =====
    @api.model
    def create(self, vals):
        """
        Créer un nouveau membre.
        
        Si aucun partner_id n'est fourni, crée automatiquement un
        contact res.partner avec les informations du membre.
        """
        if not vals.get('partner_id'):
            # Créer le partner avec les informations du membre
            partner_vals = {
                'name': vals.get('name', 'Client'),
                'customer_rank': 1,
            }
            # Ajouter email et phone seulement s'ils sont fournis
            if vals.get('email'):
                partner_vals['email'] = vals.get('email')
            if vals.get('phone'):
                partner_vals['phone'] = vals.get('phone')
            
            # Le company_id sera géré automatiquement par Odoo si nécessaire
            # Ne pas le forcer pour éviter les problèmes de contrainte
            partner = self.env['res.partner'].with_context(
                default_company_id=False
            ).create(partner_vals)
            vals['partner_id'] = partner.id
            
            _logger.info(
                "Partner créé automatiquement pour le membre '%s': ID %s",
                vals.get('name'),
                partner.id
            )
        
        return super().create(vals)

    def write(self, vals):
        """
        Mettre à jour un membre.
        
        Synchronise automatiquement les modifications du nom, email
        et téléphone vers le contact res.partner associé.
        """
        # Mettre à jour le partner si les champs sont modifiés
        if 'name' in vals or 'email' in vals or 'phone' in vals:
            for rec in self:
                if rec.partner_id:
                    partner_vals = {}
                    if 'name' in vals:
                        partner_vals['name'] = vals.get('name')
                    if 'email' in vals:
                        partner_vals['email'] = vals.get('email')
                    if 'phone' in vals:
                        partner_vals['phone'] = vals.get('phone')
                    
                    if partner_vals:
                        try:
                            rec.partner_id.write(partner_vals)
                            _logger.debug(
                                "Partner %s mis à jour avec: %s",
                                rec.partner_id.id,
                                partner_vals
                            )
                        except Exception as e:
                            # Logger l'erreur mais ne pas bloquer la mise à jour du membre
                            _logger.warning(
                                "Erreur lors de la mise à jour du partner %s pour le membre %s: %s",
                                rec.partner_id.id,
                                rec.id,
                                str(e)
                            )
        
        return super().write(vals)

    # ===== ACTIONS =====
    def action_create_reservation(self):
        """Ouvrir le formulaire de création de réservation pour ce membre."""
        self.ensure_one()
        return {
            'name': 'Nouvelle Réservation',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.reservation',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_member_id': self.id},
        }

    def action_recharge_credit(self):
        """Ouvrir le wizard de recharge de crédit pour ce membre."""
        self.ensure_one()
        return {
            'name': 'Recharger Crédit',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.credit.recharge',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_member_id': self.id},
        }

    def action_view_reservations(self):
        """Voir toutes les réservations de ce membre."""
        self.ensure_one()
        return {
            'name': f'Réservations de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.reservation',
            'view_mode': 'tree,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    def action_view_credit_history(self):
        """Voir l'historique de crédit de ce membre."""
        self.ensure_one()
        return {
            'name': f'Historique Crédit - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.credit.history',
            'view_mode': 'tree,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    # ===== SEARCH METHODS =====
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """
        Recherche par nom et matricule.
        
        Permet de trouver un membre en tapant soit son nom soit son matricule.
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('matricule', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, order=order)

    def name_get(self):
        """Afficher le nom avec le matricule si disponible."""
        result = []
        for rec in self:
            name = rec.name
            if rec.matricule:
                name = f"[{rec.matricule}] {name}"
            result.append((rec.id, name))
        return result
