# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class TravelInvoiceClient(models.Model):
    _name = 'travel.invoice.client'
    _description = 'Facture Client Travel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char('Numéro Facture', default='Nouveau', readonly=True, copy=False)
    date_invoice = fields.Date('Date Facture', default=fields.Date.context_today, required=True, tracking=True)
    
    # Société Odoo (pour multi-société)
    company_id = fields.Many2one('res.company', string='Société Odoo', default=lambda self: self.env.company, readonly=True)
    
    # Société Travel
    travel_company_id = fields.Many2one('travel.company', string='Société', 
                                        required=True, tracking=True,
                                        help="Sélectionnez la société pour filtrer les membres")
    
    # Membres de la société (plusieurs membres)
    member_ids = fields.Many2many('travel.member', 'travel_invoice_client_member_rel', 
                                 'invoice_id', 'member_id',
                                 string='Membres', 
                                 domain="[('company_id', '=', travel_company_id)]",
                                 tracking=True,
                                 help="Sélectionnez les membres de la société. Les lignes seront remplies automatiquement à partir de leurs réservations.")
    
    # Champ déprécié pour compatibilité (ne plus utiliser)
    member_id = fields.Many2one('travel.member', string='Membre (Déprécié)', 
                               compute='_compute_member_id', store=False,
                               help="Champ déprécié - Utilisez member_ids à la place")
    
    @api.depends('member_ids')
    def _compute_member_id(self):
        """Champ de compatibilité - retourne le premier membre si disponible"""
        for record in self:
            record.member_id = record.member_ids[0] if record.member_ids else False
    
    # Client société (pour compatibilité)
    company_client_id = fields.Many2one('res.partner', string='Société Cliente (Partenaire)', 
                                        domain="[('is_company', '=', True)]", 
                                        tracking=True,
                                        help="Partenaire Odoo associé (peut être rempli automatiquement)")
    company_vat = fields.Char('MF Client', related='company_client_id.vat', readonly=True)
    
    # Informations société (remplies automatiquement depuis travel.company)
    company_address = fields.Text('Adresse Société', default='', help="Adresse de la société - rempli automatiquement")
    company_phone = fields.Char('Téléphone Société', default='', help="Téléphone de la société - rempli automatiquement")
    company_mobile = fields.Char('Mobile Société', default='', help="Mobile de la société - rempli automatiquement")
    company_email = fields.Char('Email Société', default='', help="Email de la société - rempli automatiquement")
    company_vat_number = fields.Char('Matricule Fiscal', default='', help="MF de la société - rempli automatiquement")
    company_website = fields.Char('Site Web', default='', help="Site web de la société - rempli automatiquement")
    
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
                                  default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id, 
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
    amount_in_words_fr = fields.Char('Montant en lettres FR', compute='_compute_amount_in_words_fr', store=False)

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_in_words_fr(self):
        """Convertir le montant total en lettres (Français) - Force num2words"""
        from num2words import num2words
        
        for record in self:
            if record.amount_total:
                # Conversion explicite en français
                try:
                    text = num2words(record.amount_total, lang='fr')
                    # Ajout de la devise et majuscule
                    record.amount_in_words_fr = f"{text} Dinars".capitalize()
                except Exception as e:
                    # Fallback ultime et log erreur
                    record.amount_in_words_fr = "ERREUR CONVERSION: " + str(e)
            else:
                record.amount_in_words_fr = ''
    
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
    
    @api.depends()
    def _compute_company_info_seller(self):
        """Retourner les informations fixes de Agence WE CAN TRAVEL"""
        for record in self:
            record.company_name_seller = 'Agence WE CAN TRAVEL'
            record.company_address_seller = 'rue bachir aljaziri manzel gabes\ngabes'
            record.company_phone_seller = '+21625100035'
            record.company_mobile_seller = '+21623713387'
            record.company_email_seller = 'sales@we-cantravel.com'
            record.company_vat_seller = '1670453m'
            record.company_bank_name = 'Banque Attijari Bank'
            record.company_bank_iban = 'TN59 04 108 0650090101536 27'
    

    
    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.price_tax', 'fiscal_stamp')
    def _compute_amounts(self):
        for invoice in self:
            amount_untaxed = sum(line.price_subtotal for line in invoice.invoice_line_ids)
            amount_tax = sum(line.price_tax for line in invoice.invoice_line_ids)
            
            invoice.amount_untaxed = amount_untaxed
            invoice.amount_tax = amount_tax
            # Montant total = HT + TVA + Timbre Fiscal
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
    
    @api.onchange('travel_company_id')
    def _onchange_travel_company_id(self):
        """Remplir automatiquement les informations de société depuis travel.company"""
        if self.travel_company_id:
            # Remplir les informations de la société
            self.company_address = self.travel_company_id.address or ''
            self.company_phone = self.travel_company_id.phone or ''
            self.company_mobile = self.travel_company_id.mobile or ''
            self.company_email = self.travel_company_id.email or ''
            self.company_vat_number = self.travel_company_id.vat or ''
            self.company_website = self.travel_company_id.website or ''
            
            # Réinitialiser les membres sélectionnés
            self.member_ids = False
    
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
    
    def action_fill_lines_from_selected_members(self):
        """Remplir automatiquement les lignes de facture pour les membres sélectionnés"""
        self.ensure_one()
        if not self.travel_company_id:
            raise UserError("Veuillez sélectionner une société d'abord.")
        
        if not self.member_ids:
            raise UserError("Veuillez sélectionner au moins un membre.")
        
        # Utiliser les membres sélectionnés
        members = self.member_ids
        
        # Récupérer les réservations déjà facturées
        existing_reservation_ids = self.invoice_line_ids.mapped('reservation_id').ids
        
        # Créer les lignes de facture pour les membres sélectionnés
        lines = []
        for member in members:
            # Récupérer les réservations confirmées du membre qui ne sont pas déjà facturées
            reservations = member.reservation_ids.filtered(
                lambda r: r.status in ['confirmed', 'done'] 
                and r.total_price > 0 
                and r.id not in existing_reservation_ids
            )
            
            for reservation in reservations:
                # Utiliser total_price ou price selon ce qui est disponible
                price = reservation.total_price if reservation.total_price > 0 else (reservation.price or 0.0)
                
                if price > 0:
                    description = f"Réservation {reservation.name or 'N/A'}"
                    if reservation.destination_id:
                        description += f" - {reservation.destination_id.name}"
                    if reservation.check_in and reservation.check_out:
                        description += f" ({reservation.check_in} au {reservation.check_out})"
                    
                    lines.append((0, 0, {
                        'passenger_id': member.id,
                        'reference': f"R-{str(reservation.id).zfill(5)}",
                        'description': description,
                        'destination_id': reservation.destination_id.id if reservation.destination_id else False,
                        'reservation_id': reservation.id,
                        'quantity': 1.0,
                        'price_ttc': price,  # Le prix de la réservation est TTC
                        'tax_rate': '7',  # Par défaut 7%, peut être modifié
                    }))
        
        if lines:
            # Ajouter les nouvelles lignes aux lignes existantes
            self.write({'invoice_line_ids': lines})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lignes remplies',
                    'message': f'{len(lines)} ligne(s) de facturation ajoutée(s) pour {len(members)} membre(s).',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            raise UserError("Aucune ligne n'a pu être créée. Vérifiez que les membres sélectionnés ont des réservations avec un prix.")


class TravelInvoiceClientLine(models.Model):
    _name = 'travel.invoice.client.line'
    _description = 'Ligne Facture Client Travel'
    _order = 'sequence, id'

    sequence = fields.Integer('Séquence', default=10)
    invoice_id = fields.Many2one('travel.invoice.client', string='Facture', required=True, ondelete='cascade')
    
    # Référence passager/client
    passenger_id = fields.Many2one('travel.member', string='Membre', 
                                   required=True)
    reference = fields.Char('Référence', help='Ex: P-00001')
    
    # Voyage/Destination
    destination_id = fields.Many2one('travel.destination', string='Voyage', 
                                     help="Nom du voyage - rempli automatiquement depuis les réservations du membre")
    
    # Détails du voyage
    description = fields.Text('Description', required=True)
    reservation_id = fields.Many2one('travel.reservation', string='Réservation liée')
    
    # Quantité et Prix
    quantity = fields.Float('Quantité', default=1.0, required=True)
    uom = fields.Char('Unité', default='d', help='Unité de mesure (ex: j pour jour)')
    price_ttc = fields.Monetary('Prix TTC Saisi', required=True, currency_field='currency_id', 
                                help="Prix TTC (Total avec taxe) saisi dans la réservation")
    price_unit = fields.Monetary('PU HT', compute='_compute_price_ht', store=True, currency_field='currency_id',
                                 help="Prix HT calculé = Prix TTC - 7%")
    
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
    
    @api.depends('quantity', 'price_ttc', 'tax_rate')
    def _compute_price_ht(self):
        """Calculer le prix HT à partir du prix TTC
        Formule correcte selon utilisateur:
        1. TVA = TTC × 7%
        2. HT = TTC - TVA
        """
        for line in self:
            if line.price_ttc:
                # Calculer la TVA sur le TTC
                tax_percent = float(line.tax_rate or '0') / 100.0
                tva_amount = line.price_ttc * tax_percent
                # HT = TTC - TVA
                line.price_unit = line.price_ttc - tva_amount
            else:
                line.price_unit = 0.0
    
    @api.depends('quantity', 'price_unit', 'price_ttc', 'tax_rate')
    def _compute_price(self):
        """Calculer les montants de la ligne
        Formule: 
        - TVA = TTC × taux_tva
        - HT = TTC - TVA
        - Total = HT + TVA = TTC (cohérent!)
        """
        for line in self:
            if line.price_ttc:
                # Calculer depuis le TTC
                tax_percent = float(line.tax_rate or '0') / 100.0
                total_ttc = line.quantity * line.price_ttc
                
                # TVA = TTC × taux
                tax_amount = total_ttc * tax_percent
                
                # HT = TTC - TVA
                subtotal = total_ttc - tax_amount
                
                line.price_subtotal = subtotal
                line.price_tax = tax_amount
                line.price_total = total_ttc  # Le total est égal au TTC
            else:
                line.price_subtotal = 0.0
                line.price_tax = 0.0
                line.price_total = 0.0
    
    @api.onchange('passenger_id')
    def _onchange_passenger_id(self):
        """Remplir automatiquement le voyage et le prix depuis les réservations du membre"""
        if self.passenger_id:
            self.reference = f"P-{str(self.passenger_id.id).zfill(5)}"
            
            # Récupérer les réservations confirmées du membre avec un prix
            reservations = self.passenger_id.reservation_ids.filtered(
                lambda r: r.status in ['confirmed', 'done'] and r.total_price > 0
            )
            
            if reservations:
                # Prendre la première réservation disponible (ou la plus récente)
                reservation = reservations.sorted('check_in', reverse=True)[0]
                
                # Remplir automatiquement le voyage
                if reservation.destination_id:
                    self.destination_id = reservation.destination_id.id
                
                # Remplir automatiquement le prix TTC
                price = reservation.total_price if reservation.total_price > 0 else (reservation.price or 0.0)
                if price > 0:
                    self.price_ttc = price  # Le prix de la réservation est maintenant considéré comme TTC
                
                # Remplir la description
                description = f"Réservation {reservation.name or 'N/A'}"
                if reservation.destination_id:
                    description += f" - {reservation.destination_id.name}"
                if reservation.check_in and reservation.check_out:
                    description += f" ({reservation.check_in} au {reservation.check_out})"
                self.description = description
                
                # Lier la réservation
                self.reservation_id = reservation.id
            else:
                # Réinitialiser si aucune réservation trouvée
                self.destination_id = False
                self.reservation_id = False
                self.description = f"Voyage pour {self.passenger_id.name}"
    
    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        """Mettre à jour le voyage et le prix lorsque la réservation change"""
        if self.reservation_id:
            if self.reservation_id.destination_id:
                self.destination_id = self.reservation_id.destination_id.id
            
            price = self.reservation_id.total_price if self.reservation_id.total_price > 0 else (self.reservation_id.price or 0.0)
            if price > 0:
                self.price_ttc = price  # Le prix de la réservation est maintenant considéré comme TTC
            
            # Mettre à jour la description
            description = f"Réservation {self.reservation_id.name or 'N/A'}"
            if self.reservation_id.destination_id:
                description += f" - {self.reservation_id.destination_id.name}"
            if self.reservation_id.check_in and self.reservation_id.check_out:
                description += f" ({self.reservation_id.check_in} au {self.reservation_id.check_out})"
            self.description = description
    
