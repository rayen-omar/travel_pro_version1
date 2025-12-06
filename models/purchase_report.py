# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TravelPurchaseReport(models.TransientModel):
    _name = 'travel.purchase.report'
    _description = 'Rapport des Factures Fournisseurs'

    date_from = fields.Date('Date Début', required=True, default=fields.Date.context_today)
    date_to = fields.Date('Date Fin', required=True, default=fields.Date.context_today)
    
    purchase_type = fields.Selection([
        ('all', 'Tous'),
        ('supplier', 'Fournisseurs'),
        ('hotel', 'Hôtels'),
        ('platform', 'Plateformes')
    ], string='Type', default='all')
    
    supplier_id = fields.Many2one('res.partner', string='Fournisseur spécifique', 
                                  domain="[('supplier_rank', '>', 0)]")
    
    # Résultats
    total_ht = fields.Monetary('Total HT', compute='_compute_totals', currency_field='currency_id')
    total_tva = fields.Monetary('Total TVA', compute='_compute_totals', currency_field='currency_id')
    total_ttc = fields.Monetary('Total TTC', compute='_compute_totals', currency_field='currency_id')
    total_withholding = fields.Monetary('Total Retenues', compute='_compute_totals', currency_field='currency_id')
    total_served = fields.Monetary('Total Servi', compute='_compute_totals', currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id)
    
    purchase_count = fields.Integer('Nombre de factures', compute='_compute_totals')
    
    @api.depends('date_from', 'date_to', 'purchase_type', 'supplier_id')
    def _compute_totals(self):
        for wizard in self:
            domain = [
                ('date_creation', '>=', wizard.date_from),
                ('date_creation', '<=', wizard.date_to),
                ('state', '!=', 'cancel')
            ]
            
            if wizard.purchase_type != 'all':
                domain.append(('purchase_type', '=', wizard.purchase_type))
            
            if wizard.supplier_id:
                domain.append(('supplier_id', '=', wizard.supplier_id.id))
            
            purchases = self.env['travel.purchase'].search(domain)
            
            wizard.total_ht = sum(purchases.mapped('amount_untaxed'))
            wizard.total_tva = sum(purchases.mapped('amount_tax'))
            wizard.total_ttc = sum(purchases.mapped('amount_total'))
            wizard.total_withholding = sum(purchases.mapped('amount_withholding'))
            wizard.total_served = sum(purchases.mapped('amount_served'))
            wizard.purchase_count = len(purchases)
    
    def action_view_purchases(self):
        """Afficher la liste des factures fournisseurs filtrées"""
        self.ensure_one()
        
        domain = [
            ('date_creation', '>=', self.date_from),
            ('date_creation', '<=', self.date_to),
            ('state', '!=', 'cancel')
        ]
        
        if self.purchase_type != 'all':
            domain.append(('purchase_type', '=', self.purchase_type))
        
        if self.supplier_id:
            domain.append(('supplier_id', '=', self.supplier_id.id))
        
        return {
            'name': 'Factures Fournisseurs - Période du {} au {}'.format(
                self.date_from.strftime('%d/%m/%Y'),
                self.date_to.strftime('%d/%m/%Y')
            ),
            'type': 'ir.actions.act_window',
            'res_model': 'travel.purchase',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'create': False}
        }
    
    def action_print_report(self):
        """Imprimer le rapport"""
        self.ensure_one()
        return self.env.ref('travel_pro_version1.action_report_travel_purchase').report_action(self)
    
    def action_export_excel(self):
        """
        Exporter le rapport vers Excel.
        
        Note: Cette fonctionnalité nécessite l'installation de la bibliothèque
        xlsxwriter (pip install xlsxwriter) et la configuration d'une action
        serveur pour générer le fichier Excel.
        """
        self.ensure_one()
        # Note: Implémentation future avec xlsxwriter
        # 1. Créer un workbook: workbook = xlsxwriter.Workbook(output)
        # 2. Créer une feuille: worksheet = workbook.add_worksheet()
        # 3. Formater les en-têtes et données
        # 4. Retourner l'action de téléchargement du fichier
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Export Excel',
                'message': 'Fonctionnalité d\'export Excel en cours de développement.',
                'type': 'warning',
                'sticky': False,
            }
        }
