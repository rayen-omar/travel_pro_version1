# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class CashRegisterOperation(models.Model):
    """Modèle pour les opérations de caisse (recettes et dépenses)."""
    _name = 'cash.register.operation'
    _description = 'Opération de Caisse'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, readonly=True, default='Nouveau')
    sequence_id = fields.Many2one('ir.sequence', string='Séquence')
    cash_register_id = fields.Many2one('cash.register', string='Caisse', 
                                        required=True, ondelete='cascade', tracking=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True, tracking=True)
    type = fields.Selection([
        ('receipt', 'Recette'),
        ('expense', 'Dépense'),
    ], string='Type', required=True, tracking=True)
    
    amount = fields.Float(string='Montant', required=True, tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Espèces'),
        ('check', 'Chèque'),
        ('mobile_wallet', 'Portefeuille Mobile'),
        ('card', 'Carte Bancaire'),
        ('transfer', 'Virement'),
    ], string='Mode de Paiement', required=True, tracking=True)
    
    note = fields.Text(string='Note/Référence', help='Références de cet argent', tracking=True)
    invoice_number = fields.Char(string='Numéro Facture', tracking=True)
    quote_number = fields.Char(string='Numéro Devis', tracking=True)
    
    # Relations
    invoice_id = fields.Many2one('account.move', string='Facture', tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Devis', tracking=True)
    reservation_id = fields.Many2one('travel.reservation', string='Réservation', tracking=True)
    
    user_id = fields.Many2one('res.users', string='Utilisateur', 
                              default=lambda self: self.env.user, required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Société', 
                                 related='cash_register_id.company_id', store=True, readonly=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('cancelled', 'Annulé'),
    ], string='État', default='draft', tracking=True, required=True)
    
    @api.model
    def create(self, vals):
        """Générer automatiquement la référence de l'opération."""
        if vals.get('name', 'Nouveau') == 'Nouveau':
            # Utiliser la séquence par défaut si non spécifiée
            if 'sequence_id' not in vals or not vals.get('sequence_id'):
                default_seq = self.env.ref(
                    'travel_pro_version1.seq_cash_register_operation',
                    raise_if_not_found=False
                )
                if default_seq:
                    vals['sequence_id'] = default_seq.id

            if 'sequence_id' in vals and vals['sequence_id']:
                sequence = self.env['ir.sequence'].browse(vals['sequence_id'])
                vals['name'] = sequence.next_by_id()
            else:
                # Séquence par défaut via code
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('cash.register.operation')
                    or 'Nouveau'
                )
        return super().create(vals)
    
    @api.constrains('amount')
    def _check_amount(self):
        """Vérifier que le montant est strictement positif."""
        for operation in self:
            if operation.amount <= 0:
                raise ValidationError("Le montant doit être supérieur à zéro.")

    @api.constrains('cash_register_id', 'state')
    def _check_cash_register_state(self):
        """Vérifier que la caisse est ouverte pour confirmer une opération."""
        for operation in self:
            if (operation.cash_register_id.state != 'opened' and
                    operation.state == 'confirmed'):
                raise ValidationError(
                    "La caisse doit être ouverte pour confirmer une opération."
                )

    def action_confirm(self):
        """Confirmer l'opération."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(
                "Seules les opérations en brouillon peuvent être confirmées."
            )

        if self.cash_register_id.state != 'opened':
            raise UserError(
                "La caisse doit être ouverte pour confirmer une opération."
            )

        self.write({'state': 'confirmed'})

    def action_cancel(self):
        """Annuler l'opération."""
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError("Cette opération est déjà annulée.")

        self.write({'state': 'cancelled'})

    def action_draft(self):
        """Remettre l'opération en brouillon."""
        self.ensure_one()
        self.write({'state': 'draft'})

    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        """Remplir automatiquement les informations depuis la réservation."""
        if self.reservation_id:
            # Remplir le devis si disponible
            if self.reservation_id.sale_order_id:
                self.sale_order_id = self.reservation_id.sale_order_id.id
                self.quote_number = self.reservation_id.sale_order_id.name

            # Remplir les factures si disponibles
            if self.reservation_id.invoice_ids:
                # Prendre la dernière facture
                last_invoice = self.reservation_id.invoice_ids.sorted('create_date', reverse=True)[0]
                self.invoice_id = last_invoice.id
                self.invoice_number = last_invoice.name

            # Remplir le montant depuis le reste à payer
            if self.type == 'receipt' and self.reservation_id.remaining_to_pay > 0:
                self.amount = self.reservation_id.remaining_to_pay

            # Remplir la note avec les informations de la réservation
            note_parts = [f"Réservation: {self.reservation_id.name}"]
            if self.reservation_id.destination_id:
                note_parts.append(f"Destination: {self.reservation_id.destination_id.name}")
            if self.reservation_id.member_id:
                note_parts.append(f"Client: {self.reservation_id.member_id.name}")
            self.note = " | ".join(note_parts)

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):
        """Remplir automatiquement le numéro de facture et la réservation."""
        if self.invoice_id:
            self.invoice_number = self.invoice_id.name
            # Lier automatiquement la réservation si disponible
            if self.invoice_id.reservation_id:
                self.reservation_id = self.invoice_id.reservation_id.id

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Remplir automatiquement le numéro de devis et la réservation."""
        if self.sale_order_id:
            self.quote_number = self.sale_order_id.name
            # Lier automatiquement la réservation si disponible via le POS
            if hasattr(self.sale_order_id, 'reservation_id') and self.sale_order_id.reservation_id:
                self.reservation_id = self.sale_order_id.reservation_id.id

