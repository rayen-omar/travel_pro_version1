# -*- coding: utf-8 -*-
"""
Modèle de gestion des sociétés clientes pour TravelPro.

Ce module gère les sociétés (entreprises clientes) qui peuvent
avoir plusieurs membres effectuant des réservations.
"""
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class TravelCompany(models.Model):
    """
    Société cliente de l'agence de voyage.
    
    Une société peut regrouper plusieurs membres et dispose
    d'informations de contact et fiscales.
    """
    _name = 'travel.company'
    _description = 'Société Cliente'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # ===== CONTRAINTES SQL =====
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 
         'Le nom de société doit être unique. Cette société existe déjà.'),
        ('vat_unique', 'UNIQUE(vat)', 
         'Le matricule fiscal doit être unique. Ce matricule existe déjà.'),
    ]

    # ===== CHAMPS =====
    name = fields.Char(
        'Nom', 
        required=True, 
        tracking=True,
        help="Nom de la société"
    )
    phone = fields.Char(
        'Téléphone',
        help="Numéro de téléphone fixe"
    )
    mobile = fields.Char(
        'Mobile',
        help="Numéro de téléphone mobile"
    )
    email = fields.Char(
        'Email',
        help="Adresse email de contact"
    )
    address = fields.Text(
        'Adresse',
        help="Adresse complète de la société"
    )
    website = fields.Char(
        'Site Web',
        help="URL du site web"
    )
    vat = fields.Char(
        'Matricule Fiscale', 
        help="Numéro d'identification fiscale (ex: 1234567/A/M/000)", 
        tracking=True
    )
    
    # Relations
    member_ids = fields.One2many(
        'travel.member', 
        'company_id', 
        string='Membres'
    )
    member_count = fields.Integer(
        'Nombre de Membres', 
        compute='_compute_member_count'
    )

    # ===== VALIDATIONS =====
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
                        "Le format attendu est: contact@societe.com"
                    )

    @api.constrains('vat')
    def _check_vat_format(self):
        """Valider le format du matricule fiscal tunisien."""
        for record in self:
            if record.vat:
                # Format tunisien: 7 chiffres / 1 lettre / 1 lettre / 3 chiffres
                # Ex: 1234567/A/M/000
                pattern = re.compile(r'^\d{7}/[A-Z]/[A-Z]/\d{3}$|^\d{7}[A-Z]$')
                cleaned_vat = record.vat.upper().replace(' ', '')
                if not pattern.match(cleaned_vat):
                    _logger.warning(
                        "Format de matricule fiscal non standard: %s",
                        record.vat
                    )
    
    # Champ Many2many pour sélectionner des membres existants (comme dans fournisseur)
    # Utilise compute + inverse pour synchroniser avec member_ids
    selected_member_ids = fields.Many2many(
        'travel.member',
        'company_member_selection_rel',
        'company_id',
        'member_id',
        string='Sélectionner Membres',
        compute='_compute_selected_member_ids',
        inverse='_inverse_selected_member_ids',
        help='Sélectionnez des membres existants à ajouter à cette société'
    )

    @api.depends('member_ids')
    def _compute_member_count(self):
        for rec in self:
            rec.member_count = len(rec.member_ids)
    
    @api.depends('member_ids')
    def _compute_selected_member_ids(self):
        """Synchroniser selected_member_ids avec les membres de la société"""
        for rec in self:
            rec.selected_member_ids = rec.member_ids
    
    def _inverse_selected_member_ids(self):
        """Quand on modifie selected_member_ids, mettre à jour company_id des membres"""
        for rec in self:
            # Membres à ajouter (dans selected mais pas encore liés à cette société)
            for member in rec.selected_member_ids:
                if member.company_id != rec:
                    member.company_id = rec.id
            
            # Membres à retirer (étaient liés mais plus dans la sélection)
            members_to_remove = rec.member_ids - rec.selected_member_ids
            for member in members_to_remove:
                member.company_id = False

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