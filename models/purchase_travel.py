# -*- coding: utf-8 -*-
# import base64  # Nécessaire pour l'extraction PDF future

from odoo import api, fields, models
from odoo.exceptions import UserError


class TravelPurchase(models.Model):
    _name = 'travel.purchase'
    _description = 'Facture Fournisseur Travel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc, id desc'

    name = fields.Char('Numéro Facture', readonly=True, default='Nouveau', copy=False)
    date_creation = fields.Date('Date Facture', required=True, default=fields.Date.context_today, tracking=True)
    
    # Type de facture
    purchase_type = fields.Selection([
        ('supplier', 'Fournisseur'),
        ('hotel', 'Hôtel'),
        ('platform', 'Plateforme')
    ], string='Type', required=True, default='supplier', tracking=True)
    
    # Fournisseur
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', 
                                  required=True, tracking=True,
                                  help="Le partenaire sera automatiquement marqué comme fournisseur s'il ne l'est pas déjà")
    
    # Services
    service_ids = fields.Many2many('travel.service', string='Services', 
                                   domain="[('supplier_id', '=', supplier_id)]",
                                   help="Sélectionnez les services du fournisseur. Le montant HT sera calculé automatiquement.")
    
    # Montants
    amount_ttc = fields.Monetary('Montant TTC Saisi', required=True, currency_field='currency_id', tracking=True,
                                 help="Montant TTC saisi (également calculé automatiquement à partir des services)")
    amount_untaxed = fields.Monetary('Montant HT', compute='_compute_amounts', store=True, currency_field='currency_id',
                                     help="Montant HT calculé = TTC - TVA")
    tax_rate = fields.Selection([
        ('0', '0%'),
        ('7', '7%'),
        ('13', '13%'),
        ('19', '19%')
    ], string='Taux TVA', default='19', required=True)
    
    amount_tax = fields.Monetary('Montant TVA', compute='_compute_amounts', store=True, currency_field='currency_id')
    fiscal_stamp = fields.Monetary('Timbre Fiscal', default=1.0, currency_field='currency_id')
    amount_total = fields.Monetary('Montant Final (HT + Timbre)', compute='_compute_amounts', store=True, currency_field='currency_id',
                                   help="Montant Final = HT + Timbre Fiscal (SANS la TVA)")
    
    # Retenue à la source
    withholding_rate = fields.Float('Taux Retenue (%)', default=1.0, required=True)
    amount_withholding = fields.Monetary('Montant Retenue', compute='_compute_amounts', store=True, 
                                         currency_field='currency_id', tracking=True)
    amount_served = fields.Monetary('Montant Servi', compute='_compute_amounts', store=True, 
                                    currency_field='currency_id', help='Montant HT - Retenue')
    
    # Date de paiement
    date_payment = fields.Date('Date Paiement', tracking=True)
    
    # Devise
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id, 
                                  required=True)
    
    # Lien avec réservation (optionnel)
    reservation_id = fields.Many2one('travel.reservation', string='Réservation liée')
    
    # Notes
    note = fields.Text('Notes')
    description = fields.Text('Description')
    
    # Informations société vendeur (STE WE CAN TRAVEL) - valeurs fixes
    company_name_seller = fields.Char('Nom Société Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
    company_address_seller = fields.Text('Adresse Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
    company_phone_seller = fields.Char('Téléphone Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
    company_mobile_seller = fields.Char('Mobile Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
    company_email_seller = fields.Char('Email Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
    company_vat_seller = fields.Char('Code TVA Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
    
    # Informations bancaires
    company_bank_name = fields.Char('Nom Banque', compute='_compute_company_info_seller', store=False, readonly=True)
    company_bank_iban = fields.Char('IBAN', compute='_compute_company_info_seller', store=False, readonly=True)
    
    # Montant en lettres
    amount_in_words = fields.Char('Montant en lettres', compute='_compute_amount_in_words')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('paid', 'Payé'),
        ('cancel', 'Annulé')
    ], default='draft', tracking=True, string='État')
    
    @api.depends()
    def _compute_company_info_seller(self):
        """Retourner les informations fixes de Agence WE CAN TRAVEL"""
        for record in self:
            record.company_name_seller = 'Agence WE CAN TRAVEL'
            record.company_address_seller = 'rue bachir aljaziri manzel gabes\ngabes'
            record.company_phone_seller = '+216256100035'
            record.company_mobile_seller = '+21623713387'
            record.company_email_seller = 'sales@we-cantravel.com'
            record.company_vat_seller = '1670453m'
            record.company_bank_name = 'Banque Attijari Bank'
            record.company_bank_iban = 'TN59 04 108 0650090101536 27'
    
    @api.depends('amount_total', 'currency_id')
    def _compute_amount_in_words(self):
        from num2words import num2words
        
        for record in self:
            if record.amount_total:
                # Conversion explicite en français
                text = num2words(record.amount_total, lang='fr')
                record.amount_in_words = f"{text} Dinars".capitalize()
            else:
                record.amount_in_words = ''
    
    @api.onchange('service_ids')
    def _onchange_service_ids(self):
        """Calculer automatiquement le montant TTC à partir des services sélectionnés"""
        if self.service_ids:
            # Somme des prix de tous les services sélectionnés (prix TTC)
            self.amount_ttc = sum(service.price for service in self.service_ids if service.price)
        elif not self.amount_ttc:
            # Ne réinitialiser que si le montant est vide
            self.amount_ttc = 0.0
    
    @api.depends('amount_ttc', 'tax_rate', 'withholding_rate', 'fiscal_stamp')
    def _compute_amounts(self):
        """Calculer TVA, HT et montants selon la formule:
        1. TVA = TTC × taux_tva
        2. HT = TTC - TVA
        3. Montant Final = HT + Timbre Fiscal (SANS TVA)
        """
        for record in self:
            # Calcul TVA depuis TTC
            tax_percent = float(record.tax_rate or '0') / 100.0
            amount_tax = record.amount_ttc * tax_percent
            
            # Calcul HT = TTC - TVA
            amount_untaxed = record.amount_ttc - amount_tax
            
            # Calcul retenue sur montant HT
            amount_withholding = amount_untaxed * (record.withholding_rate / 100.0)
            
            # Montant servi = HT - Retenue
            amount_served = amount_untaxed - amount_withholding
            
            record.amount_tax = amount_tax
            record.amount_untaxed = amount_untaxed
            # Montant total = HT + TVA + Timbre Fiscal
            record.amount_total = amount_untaxed + amount_tax + record.fiscal_stamp
            record.amount_withholding = amount_withholding
            record.amount_served = amount_served
    
    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        """Marquer automatiquement le partenaire comme fournisseur et réinitialiser les services"""
        if self.supplier_id:
            if self.supplier_id.supplier_rank == 0:
                self.supplier_id.supplier_rank = 1
            # Réinitialiser les services et le montant TTC lorsque le fournisseur change
            self.service_ids = False
            self.amount_ttc = 0.0

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
        """Créer une nouvelle facture fournisseur et marquer le fournisseur si nécessaire."""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = (
                self.env['ir.sequence'].next_by_code('travel.purchase')
                or 'FAC-FOUR-00001'
            )
        record = super().create(vals)
        if record.supplier_id and record.supplier_id.supplier_rank == 0:
            record.supplier_id.supplier_rank = 1
        return record
    
    def action_confirm(self):
        """Confirmer la facture fournisseur."""
        self.ensure_one()
        self.state = 'confirmed'

    def action_set_paid(self):
        """Marquer la facture fournisseur comme payée."""
        self.ensure_one()
        if not self.date_payment:
            self.date_payment = fields.Date.context_today(self)
        self.state = 'paid'

    def action_cancel(self):
        """Annuler la facture fournisseur."""
        self.ensure_one()
        self.state = 'cancel'

    def action_draft(self):
        """Remettre la facture fournisseur en brouillon."""
        self.ensure_one()
        self.state = 'draft'
    
    def action_print_purchase(self):
        """Imprimer la facture fournisseur"""
        self.ensure_one()
        return self.env.ref('travel_pro_version1.action_report_travel_purchase').report_action(self)
    

