# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import base64

class TravelPurchase(models.Model):
    _name = 'travel.purchase'
    _description = 'Achat Travel (Fournisseur/Hôtel/Plateforme)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_creation desc, id desc'

    name = fields.Char('Numéro', readonly=True, default='Nouveau', copy=False)
    date_creation = fields.Date('Date Création', required=True, default=fields.Date.context_today, tracking=True)
    
    # Type d'achat
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
    amount_untaxed = fields.Monetary('Montant HT', required=True, currency_field='currency_id', tracking=True,
                                     help="Montant HT calculé automatiquement à partir des services sélectionnés (peut être modifié manuellement)")
    tax_rate = fields.Selection([
        ('0', '0%'),
        ('7', '7%'),
        ('13', '13%'),
        ('19', '19%')
    ], string='Taux TVA', default='19', required=True)
    
    amount_tax = fields.Monetary('Montant TVA', compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_total = fields.Monetary('Total TTC', compute='_compute_amounts', store=True, currency_field='currency_id')
    
    # Retenue à la source
    withholding_rate = fields.Float('Taux Retenue (%)', default=1.0, required=True)
    amount_withholding = fields.Monetary('Montant Retenue', compute='_compute_amounts', store=True, 
                                         currency_field='currency_id', tracking=True)
    amount_served = fields.Monetary('Montant Servi', compute='_compute_amounts', store=True, 
                                    currency_field='currency_id', help='Montant Brut - Retenue')
    
    # Date de paiement
    date_payment = fields.Date('Date Paiement', tracking=True)
    
    # Facture PDF
    invoice_pdf = fields.Binary('Facture PDF', attachment=True)
    invoice_pdf_filename = fields.Char('Nom Fichier PDF')
    
    # Extraction automatique (si disponible)
    extracted_data = fields.Text('Données Extraites', readonly=True, help='Données extraites automatiquement du PDF')
    
    # Devise
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.company.currency_id, 
                                  required=True)
    
    # Lien avec réservation (optionnel)
    reservation_id = fields.Many2one('travel.reservation', string='Réservation liée')
    
    # Notes
    note = fields.Text('Notes')
    description = fields.Text('Description')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('paid', 'Payé'),
        ('cancel', 'Annulé')
    ], default='draft', tracking=True, string='État')
    
    @api.onchange('service_ids')
    def _onchange_service_ids(self):
        """Calculer automatiquement le montant HT à partir des services sélectionnés"""
        if self.service_ids:
            # Somme des prix de tous les services sélectionnés
            self.amount_untaxed = sum(service.price for service in self.service_ids if service.price)
        elif not self.amount_untaxed:
            # Ne réinitialiser que si le montant est vide
            self.amount_untaxed = 0.0
    
    @api.depends('amount_untaxed', 'tax_rate', 'withholding_rate')
    def _compute_amounts(self):
        for record in self:
            # Calcul TVA
            tax_percent = float(record.tax_rate or '0') / 100.0
            amount_tax = record.amount_untaxed * tax_percent
            
            # Calcul retenue sur montant HT
            amount_withholding = record.amount_untaxed * (record.withholding_rate / 100.0)
            
            # Montant servi = Montant brut HT - Retenue
            amount_served = record.amount_untaxed - amount_withholding
            
            record.amount_tax = amount_tax
            record.amount_total = record.amount_untaxed + amount_tax
            record.amount_withholding = amount_withholding
            record.amount_served = amount_served
    
    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        """Marquer automatiquement le partenaire comme fournisseur et réinitialiser les services"""
        if self.supplier_id:
            if self.supplier_id.supplier_rank == 0:
                self.supplier_id.supplier_rank = 1
            # Réinitialiser les services et le montant HT lorsque le fournisseur change
            self.service_ids = False
            self.amount_untaxed = 0.0

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
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('travel.purchase') or 'ACH-00001'
        record = super(TravelPurchase, self).create(vals)
        if record.supplier_id and record.supplier_id.supplier_rank == 0:
            record.supplier_id.supplier_rank = 1
        return record
    
    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirmed'
    
    def action_set_paid(self):
        self.ensure_one()
        if not self.date_payment:
            self.date_payment = fields.Date.context_today(self)
        self.state = 'paid'
    
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
    
    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'
    
    @api.onchange('invoice_pdf')
    def _onchange_invoice_pdf(self):
        """Tentative d'extraction automatique des données du PDF"""
        if self.invoice_pdf:
            try:
                # Ici vous pouvez intégrer une bibliothèque d'extraction PDF
                # Pour l'instant, on indique juste que le PDF est attaché
                self.extracted_data = "PDF attaché. Extraction automatique disponible si format standard détecté."
                
                # TODO: Implémenter l'extraction avec PyPDF2 ou pdfplumber
                # Exemple de structure à extraire:
                # - Date facture
                # - Numéro facture
                # - Montant HT
                # - TVA
                # - Total TTC
                
            except Exception as e:
                self.extracted_data = f"Erreur lors de l'extraction: {str(e)}"
    
    def action_extract_pdf_data(self):
        """Action manuelle pour extraire les données du PDF"""
        self.ensure_one()
        if not self.invoice_pdf:
            raise UserError("Aucun PDF attaché.")
        
        # TODO: Implémenter l'extraction automatique
        raise UserError("Fonctionnalité d'extraction automatique en cours de développement. "
                       "Veuillez saisir les données manuellement.")
