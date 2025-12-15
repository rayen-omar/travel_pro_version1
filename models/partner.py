from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Services liés à ce fournisseur (créés avec ce fournisseur)
    travel_service_ids = fields.One2many('travel.service', 'supplier_id', string='Services Créés')
    travel_service_count = fields.Integer('Nombre de Services', compute='_compute_travel_service_count')
    
    # Services sélectionnés pour facturation (Many2many - on peut sélectionner des services existants)
    supplier_invoice_service_ids = fields.Many2many(
        'travel.service', 
        'partner_service_invoice_rel',
        'partner_id', 
        'service_id',
        string='Services à Facturer'
    )
    
    # ===== CHAMPS FACTURATION FOURNISSEUR =====
    # Devise
    supplier_currency_id = fields.Many2one('res.currency', string='Devise', 
                                           default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id)
    
    # Service sélectionné pour facturation
    supplier_service_id = fields.Many2one('travel.service', string='Service à Facturer',
                                          help="Sélectionnez un service pour remplir automatiquement le montant")
    
    # Réservation liée
    supplier_reservation_id = fields.Many2one('travel.reservation', string='Réservation liée')
    
    # Montants
    supplier_amount_ttc = fields.Monetary('Montant TTC Saisi', currency_field='supplier_currency_id',
                                          help="Montant TTC saisi manuellement ou calculé depuis les services")
    supplier_tax_rate = fields.Selection([
        ('0', '0%'),
        ('7', '7%'),
        ('13', '13%'),
        ('19', '19%')
    ], string='Taux TVA', default='19')
    
    supplier_amount_tax = fields.Monetary('Montant TVA', compute='_compute_supplier_amounts', 
                                          store=True, currency_field='supplier_currency_id')
    supplier_amount_untaxed = fields.Monetary('Montant HT', compute='_compute_supplier_amounts', 
                                               store=True, currency_field='supplier_currency_id')
    supplier_fiscal_stamp = fields.Monetary('Timbre Fiscal', default=1.0, currency_field='supplier_currency_id')
    supplier_amount_total = fields.Monetary('Total Facture', compute='_compute_supplier_amounts', 
                                            store=True, currency_field='supplier_currency_id',
                                            help="Total = HT + TVA + Timbre Fiscal")
    
    # Retenue à la source
    supplier_withholding_rate = fields.Float('Taux Retenue (%)', default=1.0)
    supplier_amount_withholding = fields.Monetary('Montant Retenue', compute='_compute_supplier_amounts', 
                                                   store=True, currency_field='supplier_currency_id')
    supplier_amount_served = fields.Monetary('Montant Servi', compute='_compute_supplier_amounts', 
                                              store=True, currency_field='supplier_currency_id',
                                              help='Montant HT - Retenue')
    
    # Description
    supplier_description = fields.Text('Description')

    @api.depends('travel_service_ids')
    def _compute_travel_service_count(self):
        """Calculer le nombre de services pour ce fournisseur"""
        for partner in self:
            partner.travel_service_count = len(partner.travel_service_ids)
    
    def action_load_services(self):
        """Charger les services liés à ce fournisseur dans le tableau de facturation"""
        self.ensure_one()
        if self.travel_service_ids:
            self.supplier_invoice_service_ids = [(6, 0, self.travel_service_ids.ids)]
            # Calculer le montant total
            total = sum(service.price for service in self.travel_service_ids if service.price)
            self.supplier_amount_ttc = total
            # Générer la description
            desc_parts = [f"- {s.name}: {s.price:.3f} DT" for s in self.travel_service_ids if s.price]
            self.supplier_description = "\n".join(desc_parts)
        return True
    
    @api.depends('supplier_amount_ttc', 'supplier_tax_rate', 'supplier_withholding_rate', 'supplier_fiscal_stamp')
    def _compute_supplier_amounts(self):
        """Calculer TVA, HT et montants pour le fournisseur"""
        for partner in self:
            # Calcul TVA depuis TTC
            tax_percent = float(partner.supplier_tax_rate or '0') / 100.0
            amount_tax = partner.supplier_amount_ttc * tax_percent
            
            # Calcul HT = TTC - TVA
            amount_untaxed = partner.supplier_amount_ttc - amount_tax
            
            # Calcul retenue sur montant HT
            amount_withholding = amount_untaxed * (partner.supplier_withholding_rate / 100.0) if partner.supplier_withholding_rate else 0.0
            
            # Montant servi = HT - Retenue
            amount_served = amount_untaxed - amount_withholding
            
            partner.supplier_amount_tax = amount_tax
            partner.supplier_amount_untaxed = amount_untaxed
            # Total = HT + TVA + Timbre Fiscal
            partner.supplier_amount_total = amount_untaxed + amount_tax + (partner.supplier_fiscal_stamp or 0.0)
            partner.supplier_amount_withholding = amount_withholding
            partner.supplier_amount_served = amount_served
    
    @api.onchange('travel_service_ids')
    def _onchange_travel_service_ids(self):
        """Remplir automatiquement les services à facturer depuis les services liés"""
        if self.travel_service_ids and self.supplier_rank > 0:
            # Ajouter automatiquement les services liés au tableau de facturation
            self.supplier_invoice_service_ids = [(6, 0, self.travel_service_ids.ids)]
    
    @api.onchange('supplier_invoice_service_ids')
    def _onchange_supplier_invoice_service_ids(self):
        """Calculer automatiquement le montant TTC depuis les services sélectionnés"""
        if self.supplier_invoice_service_ids:
            # Calculer le total de tous les services sélectionnés
            total = sum(service.price for service in self.supplier_invoice_service_ids if service.price)
            self.supplier_amount_ttc = total
            
            # Générer la description
            desc_parts = []
            for service in self.supplier_invoice_service_ids:
                desc_parts.append(f"- {service.name}: {service.price:.3f} DT")
            self.supplier_description = "\n".join(desc_parts) if desc_parts else ""
            
            # Sélectionner le premier service
            self.supplier_service_id = self.supplier_invoice_service_ids[0] if self.supplier_invoice_service_ids else False
        else:
            self.supplier_amount_ttc = 0
            self.supplier_description = ""
            self.supplier_service_id = False
    
    @api.onchange('supplier_service_id')
    def _onchange_supplier_service_id(self):
        """Remplir automatiquement le montant TTC depuis le service sélectionné (si un seul)"""
        if self.supplier_service_id and not self.supplier_invoice_service_ids:
            self.supplier_amount_ttc = self.supplier_service_id.price or 0
            service = self.supplier_service_id
            desc_parts = [f"Service: {service.name}"]
            if service.type:
                type_labels = {'hebergement': 'Hébergement', 'transport': 'Transport', 
                              'activite': 'Activité', 'autre': 'Autre'}
                desc_parts.append(f"Type: {type_labels.get(service.type, service.type)}")
            if service.destination_id:
                desc_parts.append(f"Destination: {service.destination_id.name}")
            if service.price:
                desc_parts.append(f"Prix: {service.price:.3f} DT")
            self.supplier_description = " | ".join(desc_parts)

    def action_create_service(self):
        """Créer un service depuis ce fournisseur"""
        self.ensure_one()
        # S'assurer que le partenaire est marqué comme fournisseur
        if self.supplier_rank == 0:
            self.supplier_rank = 1
        
        # Créer le service avec le fournisseur pré-rempli
        return {
            'name': _('Créer un Service'),
            'type': 'ir.actions.act_window',
            'res_model': 'travel.service',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_supplier_id': self.id,
                'default_name': self.name,
            }
        }

    def action_view_services(self):
        """Voir les services de ce fournisseur"""
        self.ensure_one()
        return {
            'name': _('Services du Fournisseur'),
            'type': 'ir.actions.act_window',
            'res_model': 'travel.service',
            'view_mode': 'tree,form',
            'domain': [('supplier_id', '=', self.id)],
            'context': {'default_supplier_id': self.id}
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_travel_member(self):
        """Empêche la suppression d'un partner s'il est utilisé par un travel.member"""
        travel_members = self.env['travel.member'].search([('partner_id', 'in', self.ids)])
        if travel_members:
            raise UserError(_(
                "Vous ne pouvez pas supprimer ce contact car il est utilisé par un ou plusieurs membres.\n"
                "Supprimez d'abord les membres associés, ou archivez le contact au lieu de le supprimer."
            ))

