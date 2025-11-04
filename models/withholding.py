# -*- coding: utf-8 -*-
from odoo import models, fields, api

class TravelWithholding(models.Model):
    _name = 'travel.withholding'
    _description = 'Retenue à la Source Fournisseur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_payment desc, id desc'

    name = fields.Char('Numéro', readonly=True, default='Nouveau', copy=False)
    date_payment = fields.Date('Date Versement', required=True, default=fields.Date.context_today, tracking=True)
    supplier_id = fields.Many2one('res.partner', string='Fournisseur', 
                                  required=True, tracking=True,
                                  help="Le partenaire sera automatiquement marqué comme fournisseur s'il ne l'est pas déjà")
    
    # Montants
    amount_gross = fields.Monetary('Montant Brut', required=True, currency_field='currency_id', tracking=True)
    withholding_rate = fields.Float('Taux Retenue (%)', default=1.0, required=True)
    amount_withholding = fields.Monetary('Montant Retenue', compute='_compute_withholding', store=True, 
                                         currency_field='currency_id')
    
    # Date de retenue (optionnelle, si différente de la date de versement)
    date_withholding = fields.Date('Date Retenue', tracking=True)
    
    # Devise
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.company.currency_id, 
                                  required=True)
    
    # Notes
    note = fields.Text('Notes')
    
    # Lien avec achat si nécessaire
    purchase_id = fields.Many2one('travel.purchase', string='Achat lié')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Effectué'),
        ('cancel', 'Annulé')
    ], default='draft', tracking=True, string='État')
    
    @api.depends('amount_gross', 'withholding_rate')
    def _compute_withholding(self):
        for record in self:
            record.amount_withholding = record.amount_gross * (record.withholding_rate / 100.0)
    
    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        """Marquer automatiquement le partenaire comme fournisseur"""
        if self.supplier_id and self.supplier_id.supplier_rank == 0:
            self.supplier_id.supplier_rank = 1

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
            vals['name'] = self.env['ir.sequence'].next_by_code('travel.withholding') or 'RET-00001'
        record = super(TravelWithholding, self).create(vals)
        if record.supplier_id and record.supplier_id.supplier_rank == 0:
            record.supplier_id.supplier_rank = 1
        return record
    
    def action_confirm(self):
        self.ensure_one()
        self.state = 'done'
    
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
    
    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'
