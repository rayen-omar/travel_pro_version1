# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class TravelInvoiceClient(models.Model):
    _name = 'travel.invoice.client'
    _description = 'Facture Client Travel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char('Numéro Facture', default='Nouveau', readonly=True, copy=False)
    date_invoice = fields.Date('Date Facture', default=fields.Date.context_today, required=True, tracking=True)
    
    # Client société
    company_client_id = fields.Many2one('res.partner', string='Société Cliente', 
                                        domain="[('is_company', '=', True)]", 
                                        required=True, tracking=True)
    company_vat = fields.Char('MF Client', related='company_client_id.vat', readonly=True)
    
    # Lignes de facturation (plusieurs passagers)
    invoice_line_ids = fields.One2many('travel.invoice.client.line', 'invoice_id', 
                                       string='Lignes de Facturation')
    
    # Totaux
    amount_untaxed = fields.Monetary('Total HT', compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_tax = fields.Monetary('Total TVA', compute='_compute_amounts', store=True, currency_field='currency_id')
    fiscal_stamp = fields.Monetary('Timbre Fiscal', default=1.0, currency_field='currency_id')
    amount_total = fields.Monetary('Total TTC', compute='_compute_amounts', store=True, currency_field='currency_id')
    
    # Retenues optionnelles
    apply_withholding_tax = fields.Boolean('Appliquer Retenue 1%', default=False)
    withholding_tax_amount = fields.Monetary('Retenue 1%', compute='_compute_withholding', store=True, currency_field='currency_id')
    
    apply_vat_withholding = fields.Boolean('Appliquer Retenue 25% TVA', default=False)
    vat_withholding_amount = fields.Monetary('Retenue 25% TVA', compute='_compute_withholding', store=True, currency_field='currency_id')
    
    total_withholding = fields.Monetary('Total Retenues', compute='_compute_withholding', store=True, currency_field='currency_id')
    net_to_pay = fields.Monetary('Net à Payer', compute='_compute_net_to_pay', store=True, currency_field='currency_id')
    
    # Devise
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.company.currency_id, 
                                  required=True)
    
    # État
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('paid', 'Payée'),
        ('cancel', 'Annulée')
    ], default='draft', tracking=True, string='État')
    
    # Notes
    note = fields.Text('Notes')
    amount_in_words = fields.Char('Montant en lettres', compute='_compute_amount_in_words')
    
    # Informations société
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)
    company_address = fields.Char('Adresse Société', related='company_id.street', readonly=True)
    company_vat_seller = fields.Char('Code TVA', related='company_id.vat', readonly=True)
    company_phone = fields.Char('Téléphone', related='company_id.phone', readonly=True)
    company_mobile = fields.Char('Mobile', related='company_id.mobile', readonly=True)
    company_email = fields.Char('Email', related='company_id.email', readonly=True)
    
    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.price_tax', 'fiscal_stamp')
    def _compute_amounts(self):
        for invoice in self:
            amount_untaxed = sum(line.price_subtotal for line in invoice.invoice_line_ids)
            amount_tax = sum(line.price_tax for line in invoice.invoice_line_ids)
            
            invoice.amount_untaxed = amount_untaxed
            invoice.amount_tax = amount_tax
            invoice.amount_total = amount_untaxed + amount_tax + invoice.fiscal_stamp
    
    @api.depends('amount_total', 'amount_tax', 'fiscal_stamp', 'apply_withholding_tax', 'apply_vat_withholding')
    def _compute_withholding(self):
        for invoice in self:
            withholding_tax = 0.0
            vat_withholding = 0.0
            
            if invoice.apply_withholding_tax:
                # Retenue 1% sur TTC (sans le timbre fiscal)
                base_for_withholding = invoice.amount_total - invoice.fiscal_stamp
                withholding_tax = base_for_withholding * 0.01
            
            if invoice.apply_vat_withholding:
                # Retenue 25% sur la TVA
                vat_withholding = invoice.amount_tax * 0.25
            
            invoice.withholding_tax_amount = withholding_tax
            invoice.vat_withholding_amount = vat_withholding
            invoice.total_withholding = withholding_tax + vat_withholding
    
    @api.depends('amount_total', 'total_withholding')
    def _compute_net_to_pay(self):
        for invoice in self:
            invoice.net_to_pay = invoice.amount_total - invoice.total_withholding
    
    @api.depends('net_to_pay')
    def _compute_amount_in_words(self):
        for invoice in self:
            if invoice.net_to_pay:
                # Conversion en lettres (à adapter selon les besoins)
                amount_text = invoice.currency_id.amount_to_text(invoice.net_to_pay)
                invoice.amount_in_words = amount_text
            else:
                invoice.amount_in_words = ''
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('travel.invoice.client') or 'FAC-00001'
        return super(TravelInvoiceClient, self).create(vals)
    
    def action_confirm(self):
        self.ensure_one()
        if not self.invoice_line_ids:
            raise UserError("Ajoutez au moins une ligne de facturation.")
        self.state = 'confirmed'
    
    def action_set_paid(self):
        self.ensure_one()
        self.state = 'paid'
    
    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
    
    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'
    
    def action_print_invoice(self):
        """Imprimer la facture"""
        self.ensure_one()
        return self.env.ref('travel_pro_version1.action_report_travel_invoice_client').report_action(self)


class TravelInvoiceClientLine(models.Model):
    _name = 'travel.invoice.client.line'
    _description = 'Ligne Facture Client Travel'
    _order = 'sequence, id'

    sequence = fields.Integer('Séquence', default=10)
    invoice_id = fields.Many2one('travel.invoice.client', string='Facture', required=True, ondelete='cascade')
    
    # Référence passager/client
    passenger_id = fields.Many2one('travel.member', string='Passager/Client', required=True)
    reference = fields.Char('Référence', help='Ex: P-00001')
    
    # Détails du voyage
    description = fields.Text('Description', required=True)
    reservation_id = fields.Many2one('travel.reservation', string='Réservation liée')
    
    # Quantité et Prix
    quantity = fields.Float('Quantité', default=1.0, required=True)
    uom = fields.Char('Unité', default='d', help='Unité de mesure (ex: j pour jour)')
    price_unit = fields.Monetary('PU HT', required=True, currency_field='currency_id')
    
    # TVA
    tax_rate = fields.Selection([
        ('7', '7%'),
        ('19', '19%')
    ], string='TVA', default='7', required=True)
    
    # Totaux
    price_subtotal = fields.Monetary('Total HT', compute='_compute_price', store=True, currency_field='currency_id')
    price_tax = fields.Monetary('Montant TVA', compute='_compute_price', store=True, currency_field='currency_id')
    price_total = fields.Monetary('Total TTC', compute='_compute_price', store=True, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, readonly=True)
    
    @api.depends('quantity', 'price_unit', 'tax_rate')
    def _compute_price(self):
        for line in self:
            subtotal = line.quantity * line.price_unit
            tax_percent = float(line.tax_rate or '0') / 100.0
            tax_amount = subtotal * tax_percent
            
            line.price_subtotal = subtotal
            line.price_tax = tax_amount
            line.price_total = subtotal + tax_amount
    
    @api.onchange('passenger_id')
    def _onchange_passenger_id(self):
        if self.passenger_id:
            self.reference = f"P-{str(self.passenger_id.id).zfill(5)}"
