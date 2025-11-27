# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from . import models


def post_init_hook(cr, registry):
    """
    Hook d'initialisation post-installation.
    
    Configure la devise de la société principale en TND uniquement si aucun
    élément de journal n'existe. Cela évite l'erreur lors du changement de
    devise après la création d'éléments de journal.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref('base.main_company', raise_if_not_found=False)
    tnd_currency = env.ref('base.TND', raise_if_not_found=False)

    if company and tnd_currency:
        # Vérifier s'il existe des éléments de journal pour cette société
        journal_items_exist = env['account.move.line'].sudo().search([
            ('company_id', '=', company.id)
        ], limit=1)

        # Changer la devise uniquement si aucun élément de journal n'existe
        if not journal_items_exist and company.currency_id != tnd_currency:
            company.currency_id = tnd_currency
