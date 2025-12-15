# -*- coding: utf-8 -*-
"""
Mixins réutilisables pour le module TravelPro.

Ce fichier contient des classes abstraites (mixins) qui peuvent être
héritées par d'autres modèles pour éviter la duplication de code.
"""
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SupplierAutoMixin(models.AbstractModel):
    """
    Mixin pour marquer automatiquement un partenaire comme fournisseur.
    
    Héritez de ce mixin dans les modèles qui ont un champ supplier_id
    pour automatiquement mettre à jour supplier_rank = 1 lors de la
    sélection ou sauvegarde d'un fournisseur.
    
    Usage:
        class MonModel(models.Model):
            _name = 'mon.model'
            _inherit = ['supplier.auto.mixin']
            
            supplier_id = fields.Many2one('res.partner', string='Fournisseur')
    """
    _name = 'supplier.auto.mixin'
    _description = 'Mixin Auto-Marquage Fournisseur'

    @api.onchange('supplier_id')
    def _onchange_supplier_id_auto_mark(self):
        """Marquer automatiquement le partenaire comme fournisseur lors de la sélection."""
        if hasattr(self, 'supplier_id') and self.supplier_id:
            if self.supplier_id.supplier_rank == 0:
                self.supplier_id.supplier_rank = 1
                _logger.debug(
                    "Partner %s (ID: %s) marqué comme fournisseur automatiquement",
                    self.supplier_id.name,
                    self.supplier_id.id
                )

    def _mark_supplier_on_save(self, vals):
        """
        Méthode utilitaire pour marquer un fournisseur lors de la sauvegarde.
        
        À appeler dans les méthodes write() et create() des modèles enfants.
        
        Args:
            vals (dict): Dictionnaire de valeurs à sauvegarder
            
        Returns:
            bool: True si un fournisseur a été marqué, False sinon
        """
        if 'supplier_id' in vals and vals['supplier_id']:
            supplier = self.env['res.partner'].browse(vals['supplier_id'])
            if supplier.exists() and supplier.supplier_rank == 0:
                supplier.sudo().write({'supplier_rank': 1})
                _logger.info(
                    "Partner %s (ID: %s) marqué comme fournisseur",
                    supplier.name,
                    supplier.id
                )
                return True
        return False


class EmailValidationMixin(models.AbstractModel):
    """
    Mixin pour valider le format des adresses email.
    
    Héritez de ce mixin dans les modèles qui ont un champ 'email'
    pour ajouter une validation automatique du format.
    
    Usage:
        class MonModel(models.Model):
            _name = 'mon.model'
            _inherit = ['email.validation.mixin']
            
            email = fields.Char('Email')
    """
    _name = 'email.validation.mixin'
    _description = 'Mixin Validation Email'

    # Pattern RFC 5322 simplifié pour validation email
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    @api.constrains('email')
    def _check_email_format(self):
        """Valider le format de l'email s'il est fourni."""
        for record in self:
            if hasattr(record, 'email') and record.email:
                if not self.EMAIL_PATTERN.match(record.email):
                    raise ValidationError(
                        f"Format d'email invalide: {record.email}\n"
                        "Le format attendu est: exemple@domaine.com"
                    )


class PhoneValidationMixin(models.AbstractModel):
    """
    Mixin pour valider le format des numéros de téléphone.
    
    Supporte les formats tunisiens et internationaux.
    
    Usage:
        class MonModel(models.Model):
            _name = 'mon.model'
            _inherit = ['phone.validation.mixin']
            
            phone = fields.Char('Téléphone')
    """
    _name = 'phone.validation.mixin'
    _description = 'Mixin Validation Téléphone'

    # Pattern pour numéros tunisiens et internationaux
    PHONE_PATTERN = re.compile(
        r'^(\+216\s?)?[0-9]{2}\s?[0-9]{3}\s?[0-9]{3}$|'  # Tunisie
        r'^\+?[0-9]{1,4}[\s.-]?[0-9]{1,14}$'  # International
    )

    @api.constrains('phone', 'mobile')
    def _check_phone_format(self):
        """Valider le format du téléphone s'il est fourni."""
        for record in self:
            for field_name in ['phone', 'mobile']:
                if hasattr(record, field_name):
                    phone_value = getattr(record, field_name)
                    if phone_value:
                        # Nettoyer le numéro (supprimer espaces)
                        cleaned = phone_value.replace(' ', '').replace('-', '').replace('.', '')
                        if len(cleaned) < 8:
                            raise ValidationError(
                                f"Numéro de téléphone trop court: {phone_value}\n"
                                "Le numéro doit contenir au moins 8 chiffres."
                            )


class AmountCalculationMixin(models.AbstractModel):
    """
    Mixin pour les calculs de montants TVA/HT/TTC.
    
    Fournit des méthodes utilitaires pour calculer les montants
    à partir d'un TTC ou d'un HT avec un taux de TVA donné.
    
    Usage:
        class MonModel(models.Model):
            _name = 'mon.model'
            _inherit = ['amount.calculation.mixin']
            
        def ma_methode(self):
            ht, tva = self._compute_ht_from_ttc(1000, 0.19)
    """
    _name = 'amount.calculation.mixin'
    _description = 'Mixin Calculs Montants'

    def _compute_ht_from_ttc(self, amount_ttc, tax_rate):
        """
        Calculer le montant HT et la TVA depuis un montant TTC.
        
        Formule: HT = TTC / (1 + taux_tva)
        
        Args:
            amount_ttc (float): Montant TTC
            tax_rate (float): Taux de TVA (ex: 0.19 pour 19%)
            
        Returns:
            tuple: (montant_ht, montant_tva)
        """
        if not amount_ttc:
            return 0.0, 0.0
        
        amount_ht = amount_ttc / (1 + tax_rate)
        amount_tva = amount_ttc - amount_ht
        
        return round(amount_ht, 3), round(amount_tva, 3)

    def _compute_ttc_from_ht(self, amount_ht, tax_rate):
        """
        Calculer le montant TTC et la TVA depuis un montant HT.
        
        Formule: TTC = HT * (1 + taux_tva)
        
        Args:
            amount_ht (float): Montant HT
            tax_rate (float): Taux de TVA (ex: 0.19 pour 19%)
            
        Returns:
            tuple: (montant_ttc, montant_tva)
        """
        if not amount_ht:
            return 0.0, 0.0
        
        amount_tva = amount_ht * tax_rate
        amount_ttc = amount_ht + amount_tva
        
        return round(amount_ttc, 3), round(amount_tva, 3)

    def _compute_withholding(self, amount_ht, withholding_rate):
        """
        Calculer le montant de retenue à la source.
        
        Args:
            amount_ht (float): Montant HT (base de calcul)
            withholding_rate (float): Taux de retenue (ex: 1.0 pour 1%)
            
        Returns:
            float: Montant de la retenue
        """
        if not amount_ht or not withholding_rate:
            return 0.0
        
        return round(amount_ht * (withholding_rate / 100.0), 3)


class SequenceGeneratorMixin(models.AbstractModel):
    """
    Mixin pour générer des séquences automatiques.
    
    Fournit une méthode pour générer une référence unique
    lors de la création d'un enregistrement.
    
    Usage:
        class MonModel(models.Model):
            _name = 'mon.model'
            _inherit = ['sequence.generator.mixin']
            
            name = fields.Char('Référence', default='Nouveau')
            
        @api.model
        def create(self, vals):
            vals = self._generate_sequence(vals, 'mon.sequence.code')
            return super().create(vals)
    """
    _name = 'sequence.generator.mixin'
    _description = 'Mixin Générateur de Séquence'

    def _generate_sequence(self, vals, sequence_code, field_name='name', default_value='Nouveau'):
        """
        Générer une séquence automatique si le champ est vide ou par défaut.
        
        Args:
            vals (dict): Dictionnaire de valeurs
            sequence_code (str): Code de la séquence ir.sequence
            field_name (str): Nom du champ à remplir (défaut: 'name')
            default_value (str): Valeur par défaut à remplacer (défaut: 'Nouveau')
            
        Returns:
            dict: Dictionnaire vals mis à jour
        """
        if vals.get(field_name, default_value) == default_value:
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            if sequence:
                vals[field_name] = sequence
            else:
                _logger.warning(
                    "Séquence '%s' non trouvée, utilisation de la valeur par défaut",
                    sequence_code
                )
        return vals

