# -*- coding: utf-8 -*-
"""
Modèle de facturation client pour TravelPro.

Gère les factures clients de l'agence de voyage avec calcul
automatique de la TVA, remises, retenues et montants en lettres.
"""
import logging
import re

from num2words import num2words

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


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
    company_address = fields.Char('Adresse Société', default='', help="Adresse de la société - rempli automatiquement")
    company_phone = fields.Char('Téléphone Société', default='', help="Téléphone de la société - rempli automatiquement")
    company_mobile = fields.Char('Mobile Société', default='', help="Mobile de la société - rempli automatiquement")
    company_email = fields.Char('Email Société', default='', help="Email de la société - rempli automatiquement")
    company_vat_number = fields.Char('Matricule Fiscal', default='', help="MF de la société - rempli automatiquement")
    company_website = fields.Char('Site Web', default='', help="Site web de la société - rempli automatiquement")
    member_count_global = fields.Integer('Nombre de Membres', default=1,
                                         help="Nombre global appliqué aux lignes de facture")
    
    # Lignes de facturation (plusieurs passagers)
    invoice_line_ids = fields.One2many('travel.invoice.client.line', 'invoice_id', 
                                       string='Lignes de Facturation')
    invoice_line_detailed_ids = fields.One2many(
        'travel.invoice.client.line',
        'invoice_id',
        string='Lignes Détaillées',
        domain=[('passenger_id', '!=', False)],
    )
    invoice_line_general_ids = fields.One2many(
        'travel.invoice.client.line',
        'invoice_id',
        string='Lignes Générales',
        domain=['&', ('passenger_id', '=', False), '|', ('hotel_id', '!=', False), ('service_id', '!=', False)],
    )
    
    # Totaux
    amount_untaxed = fields.Monetary('Total HT', compute='_compute_amounts', store=False, currency_field='currency_id')
    
    # Remise configurable (après Total HT)
    discount_type = fields.Selection([
        ('none', 'Pas de remise'),
        ('percent', 'Pourcentage (%)'),
        ('fixed', 'Montant fixe')
    ], string='Type de Remise', default='none', tracking=True,
       help="Choisissez le type de remise à appliquer sur le Total HT")
    discount_rate = fields.Float('Taux Remise (%)', default=0.0, 
                                  help="Pourcentage de remise à appliquer (ex: 10 pour 10%)")
    discount_fixed = fields.Monetary('Montant Remise Fixe', default=0.0, currency_field='currency_id',
                                      help="Montant fixe de remise à appliquer")
    discount_amount = fields.Monetary('Montant Remise', compute='_compute_amounts', store=False, 
                                       currency_field='currency_id',
                                       help="Montant de la remise calculée")
    amount_after_discount = fields.Monetary('Total HT Après Remise', compute='_compute_amounts', 
                                             store=False, currency_field='currency_id',
                                             help="Total HT après application de la remise")
    
    amount_tax = fields.Monetary('Total TVA', compute='_compute_amounts', store=False, currency_field='currency_id')
    
    # TVA par taux (pour affichage détaillé)
    tax_7_amount = fields.Monetary('TVA 7%', compute='_compute_amounts', store=False, currency_field='currency_id')
    tax_13_amount = fields.Monetary('TVA 13%', compute='_compute_amounts', store=False, currency_field='currency_id')
    tax_19_amount = fields.Monetary('TVA 19%', compute='_compute_amounts', store=False, currency_field='currency_id')
    tax_custom_amount = fields.Monetary('TVA Autre', compute='_compute_amounts', store=False, currency_field='currency_id')
    tax_details = fields.Text('Détails TVA', compute='_compute_amounts', store=False,
                             help="Détail des montants TVA par taux")
    
    fiscal_stamp = fields.Monetary('Timbre Fiscal', default=1.0, currency_field='currency_id')
    amount_total = fields.Monetary('Total TTC', compute='_compute_amounts', store=False, currency_field='currency_id')
    
    # Retenues optionnelles
    apply_withholding_tax = fields.Boolean('Appliquer Retenue 1%', default=False)
    withholding_tax_amount = fields.Monetary('Retenue 1%', compute='_compute_withholding', store=False, currency_field='currency_id')
    
    apply_vat_withholding = fields.Boolean('Appliquer Retenue 25% TVA', default=False)
    vat_withholding_amount = fields.Monetary('Retenue 25% TVA', compute='_compute_withholding', store=False, currency_field='currency_id')
    
    total_withholding = fields.Monetary('Total Retenues', compute='_compute_withholding', store=False, currency_field='currency_id')
    net_to_pay = fields.Monetary('Net à Payer', compute='_compute_net_to_pay', store=False, currency_field='currency_id')
    
    # Devise
    currency_id = fields.Many2one('res.currency', string='Devise', 
                                  default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id, 
                                  required=True)
    
    # Type de template
    invoice_template_type = fields.Selection([
        ('detailed', 'Détaillé (par membre)'),
        ('general', 'Général (par voyage)')
    ], string='Type de Template', default='detailed', required=True,
       help="Détaillé: Affiche chaque membre dans une ligne séparée\nGénéral: Regroupe par voyage avec nombre de membres")
    
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

    def _format_amount_in_words(self, amount):
        """Formater le montant en lettres français avec corrections."""
        try:
            amount_int = int(round(amount))
            text = num2words(amount_int, lang='fr')
            # Corrections spécifiques pour les erreurs courantes
            # Remplacer "Mlle" (abréviation erronée) par "mille"
            text = re.sub(r'\bMlle\b', 'mille', text, flags=re.IGNORECASE)
            text = re.sub(r'\bMLLE\b', 'mille', text)
            # Capitaliser la première lettre
            if text:
                text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
            return text
        except Exception as e:
            _logger.error("Erreur conversion montant %s en lettres: %s", amount, str(e))
            return f"{amount:.0f}"
    
    @api.depends('amount_total', 'currency_id')
    def _compute_amount_in_words_fr(self):
        """Convertir le montant total en lettres (Français)."""
        for record in self:
            if record.amount_total:
                text = self._format_amount_in_words(record.amount_total)
                record.amount_in_words_fr = f"{text} Dinars"
            else:
                record.amount_in_words_fr = ''
    
    # Informations société vendeur (STE WE CAN TRAVEL) - valeurs fixes
    company_name_seller = fields.Char('Nom Société Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
    company_address_seller = fields.Char('Adresse Vendeur', compute='_compute_company_info_seller', store=False, readonly=True)
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
            record.company_address_seller = 'rue bachir aljaziri manzel gabes, gabes'
            record.company_phone_seller = '+21625100035'
            record.company_mobile_seller = '+21623713387'
            record.company_email_seller = 'sales@we-cantravel.com'
            record.company_vat_seller = '1670453M'
            record.company_bank_name = 'Banque Attijari Bank'
            record.company_bank_iban = 'TN59 04 108 0650090101536 27'
    

    
    @api.depends('invoice_line_ids.price_ttc', 'invoice_line_ids.tax_rate', 'invoice_line_ids.tax_rate_custom',
                 'invoice_line_ids.member_count',
                 'invoice_line_ids.service_id', 'invoice_line_ids.passenger_id',
                 'fiscal_stamp',
                 'discount_type', 'discount_rate', 'discount_fixed')
    def _compute_amounts(self):
        for invoice in self:
            # Calcul des montants directement depuis les champs source pour éviter
            # les écarts quand member_count change.
            amount_untaxed = 0.0

            # Calculer la TVA par taux depuis les lignes
            # Grouper les TVA par taux
            tax_by_rate = {}
            tax_details_list = []
            
            for line in invoice.invoice_line_ids:
                if not (line.price_ttc or line.is_ticket):
                    continue

                tax_percent = line._get_tax_rate_value() / 100.0
                total_ttc = line._get_effective_quantity() * line.price_ttc
                
                if line.is_ticket:
                    total_commission = line._get_effective_quantity() * line.commission
                    total_ticket = line._get_effective_quantity() * line.ticket_price
                    line_tax = total_commission * tax_percent
                    line_subtotal = total_ticket + total_commission
                else:
                    line_subtotal = total_ttc / (1 + tax_percent) if (1 + tax_percent) else 0.0
                    line_tax = line_subtotal * tax_percent

                amount_untaxed += line_subtotal

                if line_tax > 0:
                    # Obtenir le taux et son libellé
                    if line.tax_rate == '7':
                        rate_key = '7%'
                        rate_label = 'TVA 7%'
                    elif line.tax_rate == '13':
                        rate_key = '13%'
                        rate_label = 'TVA 13%'
                    elif line.tax_rate == '19':
                        rate_key = '19%'
                        rate_label = 'TVA 19%'
                    elif line.tax_rate == '0':
                        rate_key = '0%'
                        rate_label = 'Sans TVA'
                    else:  # custom
                        rate_key = f"{line.tax_rate_custom}%"
                        rate_label = f"TVA {line.tax_rate_custom}%"
                    
                    # Ajouter au total par taux
                    if rate_key not in tax_by_rate:
                        tax_by_rate[rate_key] = {
                            'label': rate_label,
                            'amount': 0.0
                        }
                    tax_by_rate[rate_key]['amount'] += line_tax
            
            # Calcul de la remise selon le type (sur le Total HT)
            discount_amount = 0.0
            if invoice.discount_type == 'percent' and invoice.discount_rate > 0:
                # Remise en pourcentage sur le Total HT
                discount_amount = amount_untaxed * (invoice.discount_rate / 100.0)
            elif invoice.discount_type == 'fixed' and invoice.discount_fixed > 0:
                # Remise fixe (ne peut pas dépasser le Total HT)
                discount_amount = min(invoice.discount_fixed, amount_untaxed)
            
            # Total HT après remise (MT HT)
            amount_after_discount = amount_untaxed - discount_amount
            
            # Calculer le ratio de remise pour appliquer proportionnellement à la TVA
            if amount_untaxed > 0:
                discount_ratio = amount_after_discount / amount_untaxed
            else:
                discount_ratio = 1.0
            
            # Appliquer la remise proportionnellement à chaque taux de TVA
            total_tax_after_discount = 0.0
            tax_7_amount = 0.0
            tax_13_amount = 0.0
            tax_19_amount = 0.0
            tax_custom_amount = 0.0
            
            for rate_key, tax_info in tax_by_rate.items():
                tax_amount_before_discount = tax_info['amount']
                tax_amount_after_discount = tax_amount_before_discount * discount_ratio
                total_tax_after_discount += tax_amount_after_discount
                
                # Stocker par type pour affichage
                if rate_key == '7%':
                    tax_7_amount = tax_amount_after_discount
                elif rate_key == '13%':
                    tax_13_amount = tax_amount_after_discount
                elif rate_key == '19%':
                    tax_19_amount = tax_amount_after_discount
                else:
                    tax_custom_amount += tax_amount_after_discount
                
                # Ajouter au détail
                tax_details_list.append(
                    f"{tax_info['label']}: {tax_amount_after_discount:.3f} DT"
                )
            
            invoice.amount_untaxed = amount_untaxed
            invoice.discount_amount = discount_amount
            invoice.amount_after_discount = amount_after_discount
            invoice.amount_tax = total_tax_after_discount
            invoice.tax_7_amount = tax_7_amount
            invoice.tax_13_amount = tax_13_amount
            invoice.tax_19_amount = tax_19_amount
            invoice.tax_custom_amount = tax_custom_amount
            invoice.tax_details = "\n".join(tax_details_list) if tax_details_list else ""
            # Montant total = MT HT + TVA (après remise) + Timbre Fiscal
            invoice.amount_total = amount_after_discount + total_tax_after_discount + invoice.fiscal_stamp
    
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

    @api.onchange('invoice_line_ids', 'invoice_line_ids.member_count',
                  'invoice_line_ids.price_ttc', 'invoice_line_ids.tax_rate', 'invoice_line_ids.tax_rate_custom',
                  'invoice_line_ids.service_id', 'invoice_line_ids.passenger_id', 'invoice_line_ids.hotel_id',
                  'invoice_line_ids.reservation_id', 'discount_type', 'discount_rate', 'discount_fixed', 'fiscal_stamp')
    def _onchange_recompute_invoice_totals(self):
        for invoice in self:
            if invoice.invoice_line_ids:
                invoice.invoice_line_ids._compute_price()
            invoice._compute_amounts()
    
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
        """Imprimer la facture selon le type de template choisi"""
        self.ensure_one()
        if self.invoice_template_type == 'general':
            return self.env.ref('travel_pro_version1.action_report_travel_invoice_client_general').report_action(self)
        else:
            return self.env.ref('travel_pro_version1.action_report_travel_invoice_client').report_action(self)

    def _get_grouped_lines_by_destination(self):
        """Retourner des lignes agrégées pour le template général.

        Format cible: une ligne Hôtel (nombre, hôtel, description, prix TTC, TVA,
        montant TVA) et des lignes Service séparées.
        """
        self.ensure_one()

        def _rate_label(line):
            if line.tax_rate == '7':
                return '7%'
            if line.tax_rate == '13':
                return '13%'
            if line.tax_rate == '19':
                return '19%'
            if line.tax_rate == '0':
                return '0%'
            if line.tax_rate == 'custom' and line.tax_rate_custom:
                return f"{line.tax_rate_custom}%"
            return ''

        hotels = {}
        services = {}

        for line in self.invoice_line_ids:
            destination = line.destination_id.name if line.destination_id else 'Sans destination'
            hotel_name = (
                line.hotel_id.name
                or (line.reservation_id.hotel_service_id.name if line.reservation_id and line.reservation_id.hotel_service_id else False)
                or 'Hôtel'
            )

            is_hotel_service = bool(line.service_id and line.service_id.type == 'hebergement')
            is_service_line = bool(line.service_id and not line.passenger_id and not is_hotel_service)

            if is_service_line:
                service_name = line.service_id.name or 'Service'
                key = (destination, service_name)
                if key not in services:
                    services[key] = {
                        'sort_type': 2,
                        'destination': destination,
                        'type': 'service',
                        'count': 0.0,
                        'hotel_name': service_name,
                        'description_summary': line.description or service_name,
                        'total_price': 0.0,
                        'total_tax': 0.0,
                        'tax_rates': set(),
                    }
                services[key]['count'] += line._get_effective_quantity() or 0.0
                services[key]['total_price'] += (line.price_ttc or 0.0) * (line._get_effective_quantity() or 0.0)
                services[key]['total_tax'] += line.price_tax or 0.0
                rate = _rate_label(line)
                if rate:
                    services[key]['tax_rates'].add(rate)
            else:
                key = (destination, hotel_name)
                if key not in hotels:
                    hotels[key] = {
                        'sort_type': 1,
                        'destination': destination,
                        'type': 'hotel',
                        'count': 0,
                        'hotel_name': hotel_name,
                        'descriptions': [],
                        'description_summary': '',
                        'total_price': 0.0,
                        'total_tax': 0.0,
                        'tax_rates': set(),
                    }

                line_count = line._get_effective_quantity() or 0.0
                hotels[key]['count'] += line_count
                if line.description:
                    hotels[key]['descriptions'].append(line.description)
                hotels[key]['total_price'] += (line.price_ttc or 0.0) * (line._get_effective_quantity() or 0.0)
                hotels[key]['total_tax'] += line.price_tax or 0.0
                rate = _rate_label(line)
                if rate:
                    hotels[key]['tax_rates'].add(rate)

        result = []
        for data in hotels.values():
            if isinstance(data.get('count'), float) and data['count'].is_integer():
                data['count'] = int(data['count'])
            if data['descriptions']:
                data['description_summary'] = ' | '.join(data['descriptions'][:2])
                if len(data['descriptions']) > 2:
                    data['description_summary'] += f" ... et {len(data['descriptions']) - 2} autre(s)"
            else:
                data['description_summary'] = data['hotel_name']

            if len(data['tax_rates']) == 1:
                data['tax_rate_display'] = list(data['tax_rates'])[0]
            elif len(data['tax_rates']) > 1:
                data['tax_rate_display'] = 'Mixte'
            else:
                data['tax_rate_display'] = ''
            result.append(data)

        for data in services.values():
            if isinstance(data.get('count'), float) and data['count'].is_integer():
                data['count'] = int(data['count'])
            if len(data['tax_rates']) == 1:
                data['tax_rate_display'] = list(data['tax_rates'])[0]
            elif len(data['tax_rates']) > 1:
                data['tax_rate_display'] = 'Mixte'
            else:
                data['tax_rate_display'] = ''
            result.append(data)

        return sorted(result, key=lambda r: (r.get('destination') or '', r.get('sort_type', 9), r.get('hotel_name') or ''))
    
    def action_pay_cash(self):
        """Ouvrir un formulaire pour enregistrer le paiement en caisse"""
        self.ensure_one()
        
        # Vérifier qu'il y a un montant à payer
        if self.amount_total <= 0:
            raise UserError("Le montant de la facture doit être supérieur à zéro.")
        
        # Préparer la description pour l'opération de caisse
        description = f"Paiement facture {self.name}"
        if self.travel_company_id:
            description += f" - {self.travel_company_id.name}"
        
        # Récupérer la première réservation liée et ses informations
        reservation_id = False
        sale_order_id = False
        quote_number = False
        
        if self.invoice_line_ids:
            for line in self.invoice_line_ids:
                if line.reservation_id:
                    reservation = line.reservation_id
                    reservation_id = reservation.id
                    
                    # Récupérer le devis lié à la réservation
                    if reservation.sale_order_id:
                        sale_order_id = reservation.sale_order_id.id
                        quote_number = reservation.sale_order_id.name
                    break
        
        # Préparer le contexte avec toutes les valeurs par défaut
        context = {
            'default_type': 'receipt',
            'default_amount': self.net_to_pay if self.total_withholding > 0 else self.amount_total,
            'default_note': description,
            'default_invoice_number': self.name,
            'default_payment_method': 'cash',
        }
        
        # Ajouter la réservation si disponible
        if reservation_id:
            context['default_reservation_id'] = reservation_id
        
        # Ajouter le devis si disponible
        if sale_order_id:
            context['default_sale_order_id'] = sale_order_id
        if quote_number:
            context['default_quote_number'] = quote_number
        
        # Ouvrir le formulaire de création d'opération de caisse
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enregistrer Paiement Caisse',
            'res_model': 'cash.register.operation',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }
    
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
                        'hotel_id': reservation.hotel_service_id.id if reservation.hotel_service_id else False,
                        'member_count': reservation.participants or 1,
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
    
    # Référence passager/client (optionnel - ligne peut être pour un membre OU un service)
    passenger_id = fields.Many2one('travel.member', string='Membre',
                                   help="Membre associé à cette ligne (optionnel si un service est sélectionné)")
    reference = fields.Char('Référence', help='Ex: P-00001')
    
    # Voyage/Destination
    destination_id = fields.Many2one('travel.destination', string='Voyage', 
                                     help="Nom du voyage - rempli automatiquement depuis les réservations du membre ou le service")
    hotel_id = fields.Many2one('travel.service', string='Hôtel', domain="[('type', '=', 'hebergement')]",
                               help="Hôtel lié à la ligne de facturation")
    member_count = fields.Integer('Nb Membres', default=1,
                                  help="Nombre de membres pour cette ligne")
    
    # Détails du voyage
    description = fields.Text('Description')
    reservation_id = fields.Many2one('travel.reservation', string='Réservation liée')
    service_id = fields.Many2one('travel.service', string='Service',
                                 help="Service associé à cette ligne (peut être créé directement depuis ici)")
    credit_info = fields.Text('Info Crédit', compute='_compute_credit_info', store=False,
                              help="Information sur l'utilisation du crédit depuis la réservation")
    
    # Quantité et Prix
    quantity = fields.Float('Quantité', default=1.0, required=True, readonly=True)
    uom = fields.Char('Unité', default='d', help='Unité de mesure (ex: j pour jour)')
    price_ttc = fields.Monetary('Prix TTC Saisi', required=True, currency_field='currency_id', 
                                help="Prix TTC (Total avec taxe) saisi dans la réservation")
    price_unit = fields.Monetary('PU HT', compute='_compute_price_ht', store=False, currency_field='currency_id',
                                 help="Prix HT calculé = Prix TTC - 7%")
    
    # Billet
    is_ticket = fields.Boolean('Est un billet', default=False)
    ticket_price = fields.Monetary('Prix Billet', currency_field='currency_id')
    commission = fields.Monetary('Commission HT', currency_field='currency_id')
    
    # TVA
    tax_rate = fields.Selection([
        ('0', 'Sans TVA'),
        ('7', '7%'),
        ('13', '13%'),
        ('19', '19%'),
        ('custom', 'Autre (personnalisé)')
    ], string='TVA', default='7', required=True)
    tax_rate_custom = fields.Float('Taux TVA Personnalisé (%)', 
                                   help="Saisissez le taux de TVA en pourcentage (ex: 13 pour 13%)",
                                   digits=(16, 2))
    
    # Totaux
    price_subtotal = fields.Monetary('Total HT', compute='_compute_price', store=False, currency_field='currency_id')
    price_tax = fields.Monetary('Montant TVA', compute='_compute_price', store=False, currency_field='currency_id')
    price_total = fields.Monetary('Total TTC', compute='_compute_price', store=False, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, readonly=True)

    def write(self, vals):
        if 'member_count' not in vals:
            return super(TravelInvoiceClientLine, self).write(vals)

        # Protection contre les payloads UI qui renvoient member_count=1 par défaut
        # lors de l'édition d'autres champs dans la même ligne.
        if len(vals.keys()) > 1:
            for record in self:
                local_vals = dict(vals)
                incoming_count = local_vals.get('member_count')
                if incoming_count in (False, 0, 1) and record.member_count and record.member_count > 1:
                    local_vals['member_count'] = record.member_count
                super(TravelInvoiceClientLine, record).write(local_vals)
            return True

        return super(TravelInvoiceClientLine, self).write(vals)

    @api.onchange('member_count', 'price_ttc', 'tax_rate', 'tax_rate_custom', 'service_id', 'passenger_id', 'is_ticket', 'ticket_price', 'commission')
    def _onchange_recompute_line_and_invoice(self):
        self._compute_price()
        if self.invoice_id:
            self.invoice_id._compute_amounts()
    
    @api.depends('reservation_id', 'reservation_id.use_credit', 'reservation_id.credit_used', 
                 'reservation_id.total_price', 'reservation_id.remaining_to_pay')
    def _compute_credit_info(self):
        """Calculer les informations de crédit depuis la réservation"""
        for line in self:
            if line.reservation_id and line.reservation_id.use_credit and line.reservation_id.credit_used > 0:
                info = f"Crédit: {line.reservation_id.credit_used:.3f} DT"
                info += f"\nPayé: {line.reservation_id.credit_used:.3f} DT"
                info += f"\nReste: {line.reservation_id.remaining_to_pay:.3f} DT"
                line.credit_info = info
            else:
                line.credit_info = False
    
    @api.constrains('tax_rate', 'tax_rate_custom')
    def _check_tax_rate_custom(self):
        """Vérifier que le taux personnalisé est rempli si 'custom' est sélectionné"""
        for line in self:
            if line.tax_rate == 'custom' and (not line.tax_rate_custom or line.tax_rate_custom <= 0):
                raise ValidationError(
                    "Veuillez saisir un taux TVA personnalisé valide (supérieur à 0) "
                    "lorsque vous sélectionnez 'Autre (personnalisé)'."
                )
    
    def _get_tax_rate_value(self):
        """Obtenir la valeur numérique du taux TVA"""
        self.ensure_one()
        if self.tax_rate == 'custom':
            return self.tax_rate_custom or 0.0
        else:
            return float(self.tax_rate or '7')

    def _get_effective_quantity(self):
        """Quantité effective de facturation.

        L'utilisateur saisit manuellement le nombre de membres.
        """
        self.ensure_one()
        if self.member_count and self.member_count > 0:
            return float(self.member_count)
        return 1.0
    
    @api.depends('member_count', 'price_ttc', 'tax_rate', 'tax_rate_custom', 'is_ticket', 'ticket_price', 'commission')
    def _compute_price_ht(self):
        """Calculer le prix HT à partir du prix TTC
        Formule correcte selon utilisateur:
        1. HT = TTC / (1 + taux_tva) (ex: TTC / 1.07)
        2. TVA = HT * taux_tva
        Sauf pour Billet: HT = Prix Billet + Commission HT
        """
        for line in self:
            if line.is_ticket or line.price_ttc:
                if line.is_ticket:
                    line.price_unit = line.ticket_price + line.commission
                else:
                    tax_percent = line._get_tax_rate_value() / 100.0
                    line.price_unit = line.price_ttc / (1 + tax_percent)
            else:
                line.price_unit = 0.0
    
    @api.depends('member_count', 'price_ttc', 'tax_rate', 'tax_rate_custom', 'is_ticket', 'ticket_price', 'commission')
    def _compute_price(self):
        """Calculer les montants de la ligne
        Formule: 
        - HT = (TTC * quantite) / (1 + taux_tva)
        - TVA = HT * taux_tva
        - Total = HT + TVA
        Sauf pour billets : TVA seulement sur Commission
        """
        for line in self:
            if line.is_ticket or line.price_ttc:
                tax_percent = line._get_tax_rate_value() / 100.0
                total_ttc = line._get_effective_quantity() * line.price_ttc
                
                if line.is_ticket:
                    total_ticket = line._get_effective_quantity() * line.ticket_price
                    total_commission = line._get_effective_quantity() * line.commission
                    tax_amount = total_commission * tax_percent
                    subtotal = total_ticket + total_commission
                else:
                    # HT = TTC / (1 + TVA)
                    subtotal = total_ttc / (1 + tax_percent)
                    # TVA = HT * taux
                    tax_amount = subtotal * tax_percent
                
                line.price_subtotal = subtotal
                line.price_tax = tax_amount
                line.price_total = subtotal + tax_amount
            else:
                line.price_subtotal = 0.0
                line.price_tax = 0.0
                line.price_total = 0.0
    
    @api.onchange('passenger_id')
    def _onchange_passenger_id(self):
        """Remplir automatiquement le voyage et le prix depuis les réservations du membre"""
        if self.passenger_id:
            # Effacer le service si un membre est sélectionné (lignes indépendantes)
            if self.service_id:
                self.service_id = False
            
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

                if reservation.hotel_service_id:
                    self.hotel_id = reservation.hotel_service_id.id

                
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
                self.hotel_id = False
                self.description = f"Voyage pour {self.passenger_id.name}"
    
    @api.onchange('reservation_id')
    def _onchange_reservation_id(self):
        """Mettre à jour le voyage et le prix lorsque la réservation change"""
        if self.reservation_id:
            if self.reservation_id.destination_id:
                self.destination_id = self.reservation_id.destination_id.id

            if self.reservation_id.hotel_service_id:
                self.hotel_id = self.reservation_id.hotel_service_id.id
            else:
                self.hotel_id = False

            
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
    
    @api.onchange('service_id')
    def _onchange_service_id(self):
        """Remplir automatiquement les champs de la ligne depuis le service sélectionné"""
        if self.service_id:
            # Effacer le membre si un service est sélectionné (lignes indépendantes)
            if self.passenger_id:
                self.passenger_id = False
                self.reservation_id = False
            
            # Remplir la destination si disponible
            if self.service_id.destination_id:
                self.destination_id = self.service_id.destination_id.id
            
            # Remplir le prix TTC
            if self.service_id.price_ttc:
                self.price_ttc = self.service_id.price_ttc
            elif self.service_id.price:
                self.price_ttc = self.service_id.price
            
            # Remplir la TVA
            if self.service_id.tax_rate:
                self.tax_rate = self.service_id.tax_rate
                if self.service_id.tax_rate == 'custom' and self.service_id.tax_rate_custom:
                    self.tax_rate_custom = self.service_id.tax_rate_custom
            
            # Remplir la description avec le nom du service
            if self.service_id.name:
                self.description = self.service_id.name

            # Si le service est un hébergement, l'utiliser comme hôtel
            if self.service_id.type == 'hebergement':
                self.hotel_id = self.service_id.id
            
            # Si le service est un billet
            if self.service_id.type == 'billet':
                self.is_ticket = True
                self.ticket_price = self.service_id.ticket_price
                self.commission = self.service_id.commission
            else:
                self.is_ticket = False
                self.ticket_price = 0.0
                self.commission = 0.0

    @api.onchange('is_ticket', 'ticket_price', 'commission', 'tax_rate', 'tax_rate_custom')
    def _onchange_ticket_fields(self):
        """Mettre à jour le prix TTC si c'est un billet et qu'on modifie ses composantes"""
        if self.is_ticket:
            tax_amount = self.commission * (self._get_tax_rate_value() / 100.0)
            self.price_ttc = self.ticket_price + self.commission + tax_amount
    
