from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Services liés à ce fournisseur
    travel_service_ids = fields.One2many('travel.service', 'supplier_id', string='Services')
    travel_service_count = fields.Integer('Nombre de Services', compute='_compute_travel_service_count')

    @api.depends('travel_service_ids')
    def _compute_travel_service_count(self):
        """Calculer le nombre de services pour ce fournisseur"""
        for partner in self:
            partner.travel_service_count = len(partner.travel_service_ids)

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

