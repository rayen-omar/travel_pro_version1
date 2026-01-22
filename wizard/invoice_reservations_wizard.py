# -*- coding: utf-8 -*-
"""
Wizard pour créer une facture à partir de plusieurs réservations sélectionnées.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class InvoiceReservationsWizard(models.TransientModel):
    _name = 'invoice.reservations.wizard'
    _description = 'Wizard Facturation Groupée de Réservations'

    # Société (remplie automatiquement si toutes les réservations sont de la même société)
    travel_company_id = fields.Many2one(
        'travel.company',
        string='Société',
        required=True,
        help="Société cliente pour la facture"
    )
    
    # Réservations sélectionnées
    reservation_ids = fields.Many2many(
        'travel.reservation',
        'invoice_wizard_reservation_rel',
        'wizard_id',
        'reservation_id',
        string='Réservations',
        required=True,
        help="Sélectionnez les réservations à facturer"
    )
    
    # Date de facture
    date_invoice = fields.Date(
        'Date Facture',
        default=fields.Date.context_today,
        required=True,
        help="Date de la facture"
    )
    
    # Informations de résumé
    total_reservations = fields.Integer(
        'Nombre de Réservations',
        compute='_compute_summary',
        store=False
    )
    total_amount = fields.Monetary(
        'Montant Total (TTC)',
        compute='_compute_summary',
        store=False,
        currency_field='currency_id'
    )
    members_count = fields.Integer(
        'Nombre de Membres',
        compute='_compute_summary',
        store=False
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.ref('base.TND', raise_if_not_found=False) or self.env.company.currency_id,
        readonly=True
    )
    
    @api.depends('reservation_ids', 'reservation_ids.total_price')
    def _compute_summary(self):
        """Calculer le résumé des réservations sélectionnées"""
        for wizard in self:
            reservations = wizard.reservation_ids
            wizard.total_reservations = len(reservations)
            wizard.total_amount = sum(reservations.mapped('total_price'))
            # Compter les membres uniques
            unique_members = reservations.mapped('member_id')
            wizard.members_count = len(unique_members)
    
    @api.model
    def default_get(self, fields_list):
        """Remplir les valeurs par défaut depuis le contexte"""
        res = super().default_get(fields_list)
        
        # Récupérer les réservations depuis le contexte
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model')
        
        if active_model == 'travel.reservation' and active_ids:
            reservations = self.env['travel.reservation'].browse(active_ids)
            
            # Vérifier que toutes les réservations peuvent être facturées
            invalid_reservations = reservations.filtered(
                lambda r: r.status not in ['confirmed', 'done'] or r.total_price <= 0
            )
            if invalid_reservations:
                raise UserError(
                    f"Certaines réservations ne peuvent pas être facturées:\n"
                    f"- Réservations non confirmées ou sans prix: {', '.join(invalid_reservations.mapped('name'))}"
                )
            
            # Récupérer la société si disponible (sans validation stricte)
            companies = reservations.mapped('member_id.company_id')
            unique_companies = companies.filtered(lambda c: c)
            
            if len(unique_companies) >= 1:
                # Prendre la première société trouvée par défaut
                res['travel_company_id'] = unique_companies[0].id
            
            res['reservation_ids'] = [(6, 0, active_ids)]
        
        return res
    
    def action_create_invoice(self):
        """Créer la facture avec toutes les réservations sélectionnées"""
        self.ensure_one()
        
        if not self.reservation_ids:
            raise UserError("Veuillez sélectionner au moins une réservation.")
        
        if not self.travel_company_id:
            raise UserError("Veuillez sélectionner une société.")
        
        # IMPORTANT: Sauvegarder les IDs des réservations avant toute manipulation
        # pour éviter qu'elles soient perdues si le wizard se ferme
        reservation_ids = self.reservation_ids.ids
        reservations = self.env['travel.reservation'].browse(reservation_ids)
        
        # Vérifier que toutes les réservations peuvent être facturées
        invalid_reservations = reservations.filtered(
            lambda r: r.status not in ['confirmed', 'done'] or r.total_price <= 0
        )
        if invalid_reservations:
            raise UserError(
                f"Certaines réservations ne peuvent pas être facturées:\n"
                f"- Réservations non confirmées ou sans prix: {', '.join(invalid_reservations.mapped('name'))}"
            )
        
        # Récupérer les membres uniques des réservations
        members = reservations.mapped('member_id')
        unique_members = members.filtered(lambda m: m)
        
        # Créer la facture
        invoice_vals = {
            'travel_company_id': self.travel_company_id.id,
            'member_ids': [(6, 0, unique_members.ids)],
            'date_invoice': self.date_invoice,
        }
        
        invoice = self.env['travel.invoice.client'].create(invoice_vals)
        
        # Créer les lignes de facture pour chaque réservation
        lines = []
        for reservation in reservations:
            if reservation.total_price > 0 and reservation.member_id:
                description = f"Réservation {reservation.name or 'N/A'}"
                if reservation.destination_id:
                    description += f" - {reservation.destination_id.name}"
                if reservation.check_in and reservation.check_out:
                    description += f" ({reservation.check_in} au {reservation.check_out})"
                
                lines.append((0, 0, {
                    'invoice_id': invoice.id,
                    'passenger_id': reservation.member_id.id,
                    'reference': f"R-{str(reservation.id).zfill(5)}",
                    'description': description,
                    'destination_id': reservation.destination_id.id if reservation.destination_id else False,
                    'reservation_id': reservation.id,
                    'quantity': 1.0,
                    'price_ttc': reservation.total_price,  # Le prix de la réservation est TTC
                    'tax_rate': '7',  # Par défaut 7%, peut être modifié
                }))
        
        if lines:
            invoice.write({'invoice_line_ids': lines})
            
            # Mettre à jour le statut des réservations si nécessaire
            # Utiliser les IDs sauvegardés pour éviter les problèmes
            confirmed_reservations = reservations.filtered(lambda r: r.status == 'confirmed')
            if confirmed_reservations:
                confirmed_reservations.write({'status': 'done'})
            
            # Retourner l'action pour ouvrir la facture
            return {
                'type': 'ir.actions.act_window',
                'name': 'Facture Créée',
                'res_model': 'travel.invoice.client',
                'res_id': invoice.id,
                'view_mode': 'form',
                'target': 'current',
                'context': self.env.context,
            }
        else:
            raise UserError("Aucune ligne n'a pu être créée. Vérifiez que les réservations ont un prix.")

