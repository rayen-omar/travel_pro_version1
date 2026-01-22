# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class CashRegister(models.Model):
    """Modèle de gestion des caisses avec caisse principale et sous-caisses."""
    _name = 'cash.register'
    _description = 'Caisse'
    _order = 'name'

    name = fields.Char(string='Nom de la Caisse', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    sequence_id = fields.Many2one('ir.sequence', string='Séquence')
    is_main = fields.Boolean(string='Caisse Principale', default=False, tracking=True)
    main_cash_id = fields.Many2one('cash.register', string='Caisse Principale', 
                                    domain=[('is_main', '=', True)], tracking=True)
    user_id = fields.Many2one('res.users', string='Utilisateur Responsable', 
                              required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Société', 
                                 default=lambda self: self.env.company, required=True)
    
    # État de la caisse
    state = fields.Selection([
        ('closed', 'Fermée'),
        ('opened', 'Ouverte'),
    ], string='État', default='closed', tracking=True, required=True)
    
    # Informations d'ouverture
    opening_date = fields.Datetime(string='Date d\'Ouverture', tracking=True)
    opening_user_id = fields.Many2one('res.users', string='Ouvert par', tracking=True)
    opening_balance = fields.Float(string='Solde d\'Ouverture', default=0.0, tracking=True)
    
    # Informations de fermeture
    closing_date = fields.Datetime(string='Date de Fermeture', tracking=True)
    closing_user_id = fields.Many2one('res.users', string='Fermé par', tracking=True)
    closing_balance = fields.Float(string='Solde de Fermeture', tracking=True)
    
    # Totaux calculés
    total_receipts = fields.Float(string='Total Recettes', compute='_compute_totals', store=True)
    total_expenses = fields.Float(string='Total Dépenses', compute='_compute_totals', store=True)
    balance = fields.Float(string='Solde', compute='_compute_balance', store=True)
    
    # Relations
    operation_ids = fields.One2many('cash.register.operation', 'cash_register_id', 
                                     string='Opérations')
    sub_cash_ids = fields.One2many('cash.register', 'main_cash_id', 
                                    string='Sous-Caisses')
    sub_cash_count = fields.Integer(string='Nombre de Sous-Caisses', 
                                     compute='_compute_sub_cash_count', store=True)
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('sub_cash_ids', 'is_main')
    def _compute_sub_cash_count(self):
        """Calculer le nombre de sous-caisses actives."""
        for cash in self:
            if cash.is_main:
                cash.sub_cash_count = len(cash.sub_cash_ids.filtered('active'))
            else:
                cash.sub_cash_count = 0

    @api.depends('operation_ids.amount', 'operation_ids.type')
    def _compute_totals(self):
        """Calculer les totaux des recettes et dépenses."""
        for cash in self:
            receipts = cash.operation_ids.filtered(lambda o: o.type == 'receipt')
            expenses = cash.operation_ids.filtered(lambda o: o.type == 'expense')
            cash.total_receipts = sum(receipts.mapped('amount'))
            cash.total_expenses = sum(expenses.mapped('amount'))

    @api.depends('opening_balance', 'total_receipts', 'total_expenses')
    def _compute_balance(self):
        """Calculer le solde actuel de la caisse."""
        for cash in self:
            cash.balance = cash.opening_balance + cash.total_receipts - cash.total_expenses
    
    @api.constrains('is_main', 'main_cash_id')
    def _check_main_cash(self):
        """
        Vérifier la cohérence de la hiérarchie des caisses.
        - Une caisse principale ne peut pas avoir de parent
        - Une sous-caisse doit avoir une caisse principale
        - Il ne peut y avoir qu'une seule caisse principale par société
        """
        for cash in self:
            if cash.is_main and cash.main_cash_id:
                raise ValidationError(
                    "Une caisse principale ne peut pas avoir de caisse principale parente."
                )
            if not cash.is_main and not cash.main_cash_id:
                raise ValidationError("Une sous-caisse doit avoir une caisse principale.")

            # Vérifier qu'il n'y a qu'une seule caisse principale par société
            if cash.is_main:
                existing_main = self.search([
                    ('is_main', '=', True),
                    ('company_id', '=', cash.company_id.id),
                    ('id', '!=', cash.id),
                    ('active', '=', True)
                ], limit=1)
                if existing_main:
                    raise ValidationError(
                        "Il ne peut y avoir qu'une seule caisse principale par société. "
                        f"Une caisse principale existe déjà: {existing_main.name}"
                    )

    @api.constrains('main_cash_id')
    def _check_sub_cash_limit(self):
        """Vérifier qu'une caisse principale ne peut avoir que deux sous-caisses maximum."""
        for cash in self:
            if not cash.is_main and cash.main_cash_id:
                sub_cashes = self.search_count([
                    ('main_cash_id', '=', cash.main_cash_id.id),
                    ('id', '!=', cash.id),
                    ('active', '=', True)
                ])
                if sub_cashes >= 2:
                    raise ValidationError(
                        "Une caisse principale ne peut avoir que deux sous-caisses maximum. "
                        f"La caisse principale {cash.main_cash_id.name} a déjà {sub_cashes} sous-caisse(s)."
                    )

    @api.constrains('code')
    def _check_code_unique(self):
        """Vérifier l'unicité du code de la caisse."""
        for cash in self:
            if self.search_count([('code', '=', cash.code), ('id', '!=', cash.id)]) > 0:
                raise ValidationError("Le code de la caisse doit être unique.")
    
    def action_open_cash(self):
        """
        Ouvrir la caisse.
        - Pour une sous-caisse: vérifie que la caisse principale est ouverte
        - Pour la caisse principale: ouvre automatiquement toutes les sous-caisses
        - Le solde d'ouverture est le solde de fermeture de la dernière session
        """
        self.ensure_one()
        if self.state == 'opened':
            raise UserError("Cette caisse est déjà ouverte.")

        # Si c'est une sous-caisse, vérifier que la caisse principale est ouverte
        if not self.is_main and self.main_cash_id:
            if self.main_cash_id.state != 'opened':
                raise UserError(
                    "La caisse principale doit être ouverte avant d'ouvrir cette sous-caisse."
                )

        # Calculer le solde d'ouverture : utiliser le solde de fermeture de la dernière session
        # Si la caisse a déjà été fermée, utiliser le closing_balance comme opening_balance
        if self.closing_balance is not None and self.closing_date:
            opening_balance = self.closing_balance
        else:
            # Si aucune fermeture précédente, utiliser 0.0
            opening_balance = 0.0

        # Si c'est la caisse principale, ouvrir toutes les sous-caisses
        if self.is_main:
            sub_cashes = self.search([
                ('main_cash_id', '=', self.id),
                ('state', '=', 'closed')
            ])
            # Pour chaque sous-caisse, calculer son solde d'ouverture
            for sub_cash in sub_cashes:
                if sub_cash.closing_balance is not None and sub_cash.closing_date:
                    sub_opening_balance = sub_cash.closing_balance
                else:
                    sub_opening_balance = 0.0
                
                sub_cash.write({
                    'state': 'opened',
                    'opening_date': fields.Datetime.now(),
                    'opening_user_id': self.env.user.id,
                    'opening_balance': sub_opening_balance,
                })

        self.write({
            'state': 'opened',
            'opening_date': fields.Datetime.now(),
            'opening_user_id': self.env.user.id,
            'opening_balance': opening_balance,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Caisse Ouverte',
                'message': f'La caisse {self.name} a été ouverte avec succès.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_close_cash(self):
        """
        Fermer la caisse principale.
        Nécessite que toutes les sous-caisses soient fermées.
        """
        self.ensure_one()
        if self.state == 'closed':
            raise UserError("Cette caisse est déjà fermée.")

        if not self.is_main:
            raise UserError("Seule la caisse principale peut être fermée manuellement.")

        # Vérifier que toutes les sous-caisses sont fermées
        sub_cashes = self.search([
            ('main_cash_id', '=', self.id),
            ('state', '=', 'opened')
        ])
        if sub_cashes:
            raise UserError(
                "Toutes les sous-caisses doivent être fermées avant de fermer la caisse principale."
            )

        closing_balance = self.balance
        self.write({
            'state': 'closed',
            'closing_date': fields.Datetime.now(),
            'closing_user_id': self.env.user.id,
            'closing_balance': closing_balance,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Caisse Fermée',
                'message': f'La caisse {self.name} a été fermée avec succès. Solde: {closing_balance:.2f}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_close_sub_cash(self):
        """Fermer une sous-caisse."""
        self.ensure_one()
        if self.is_main:
            raise UserError("Cette action est uniquement pour les sous-caisses.")

        if self.state == 'closed':
            raise UserError("Cette caisse est déjà fermée.")

        closing_balance = self.balance
        self.write({
            'state': 'closed',
            'closing_date': fields.Datetime.now(),
            'closing_user_id': self.env.user.id,
            'closing_balance': closing_balance,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sous-Caisse Fermée',
                'message': f'La sous-caisse {self.name} a été fermée avec succès. Solde: {closing_balance:.2f}',
                'type': 'success',
                'sticky': False,
            }
        }

    def cron_close_main_cash_at_midnight(self):
        """
        Cron job pour fermer automatiquement la caisse principale à minuit.
        Les erreurs sont loggées mais n'interrompent pas le processus.
        """
        main_cashes = self.search([
            ('is_main', '=', True),
            ('state', '=', 'opened')
        ])
        for cash in main_cashes:
            try:
                cash.action_close_cash()
            except Exception as e:
                # Logger l'erreur mais ne pas bloquer
                self.env['ir.logging'].sudo().create({
                    'name': 'cash.register',
                    'type': 'server',
                    'level': 'error',
                    'message': (
                        f'Erreur lors de la fermeture automatique de la caisse '
                        f'{cash.name}: {str(e)}'
                    ),
                    'path': 'cash.register',
                    'func': 'cron_close_main_cash_at_midnight',
                    'line': '1',
                })

