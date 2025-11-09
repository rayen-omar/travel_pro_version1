from odoo import models, fields, api

class TravelMember(models.Model):
    _name = 'travel.member'
    _description = 'Membre / Client'

    name = fields.Char('Nom', required=True)
    company_id = fields.Many2one('travel.company', string='Société')
    email = fields.Char('Email')
    phone = fields.Char('Téléphone')
    matricule = fields.Char('Matricule')
    reservation_ids = fields.One2many('travel.reservation', 'member_id', string='Réservations')
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='restrict')

    credit_balance = fields.Float('Solde Crédit (TND)', digits=(16, 2), compute='_compute_credit_balance', store=True, readonly=True)
    credit_history_ids = fields.One2many('travel.credit.history', 'member_id', string='Historique Crédit')

    @api.depends('credit_history_ids.amount')
    def _compute_credit_balance(self):
        for rec in self:
            rec.credit_balance = sum(h.amount for h in rec.credit_history_ids)

    @api.model
    def create(self, vals):
        if not vals.get('partner_id'):
            # Créer le partner avec les informations du membre
            partner_vals = {
                'name': vals.get('name', 'Client'),
                'customer_rank': 1,
            }
            # Ajouter email et phone seulement s'ils sont fournis
            if vals.get('email'):
                partner_vals['email'] = vals.get('email')
            if vals.get('phone'):
                partner_vals['phone'] = vals.get('phone')
            
            # Le company_id sera géré automatiquement par Odoo si nécessaire
            # Ne pas le forcer pour éviter les problèmes de contrainte
            partner = self.env['res.partner'].with_context(default_company_id=False).create(partner_vals)
            vals['partner_id'] = partner.id
        return super().create(vals)

    def write(self, vals):
        # Mettre à jour le partner si les champs sont modifiés
        for rec in self:
            if rec.partner_id and ('name' in vals or 'email' in vals or 'phone' in vals):
                partner_vals = {}
                if 'name' in vals:
                    partner_vals['name'] = vals.get('name')
                if 'email' in vals:
                    partner_vals['email'] = vals.get('email')
                if 'phone' in vals:
                    partner_vals['phone'] = vals.get('phone')
                if partner_vals:
                    try:
                        rec.partner_id.write(partner_vals)
                    except Exception:
                        # Si l'écriture du partner échoue, continuer quand même avec les autres champs
                        pass
        return super().write(vals)

    def action_create_reservation(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'travel.reservation',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_member_id': self.id},
        }

    def action_recharge_credit(self):
        return {
            'name': 'Recharger Crédit',
            'type': 'ir.actions.act_window',
            'res_model': 'travel.credit.recharge',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_member_id': self.id},
        }

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, order=None):
        """Recherche par nom et matricule"""
        from odoo.osv import expression
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('matricule', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, order=order)
