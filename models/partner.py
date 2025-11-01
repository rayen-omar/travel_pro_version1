from odoo import models, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_travel_member(self):
        """Empêche la suppression d'un partner s'il est utilisé par un travel.member"""
        travel_members = self.env['travel.member'].search([('partner_id', 'in', self.ids)])
        if travel_members:
            raise UserError(_(
                "Vous ne pouvez pas supprimer ce contact car il est utilisé par un ou plusieurs membres.\n"
                "Supprimez d'abord les membres associés, ou archivez le contact au lieu de le supprimer."
            ))

