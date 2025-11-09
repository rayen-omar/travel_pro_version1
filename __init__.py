from . import models
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """
    Set the company currency to TND only if no journal items exist.
    This prevents the error when trying to change currency after journal items are created.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref('base.main_company', raise_if_not_found=False)
    tnd_currency = env.ref('base.TND', raise_if_not_found=False)
    
    if company and tnd_currency:
        # Check if there are any journal items for this company
        journal_items_exist = env['account.move.line'].sudo().search([
            ('company_id', '=', company.id)
        ], limit=1)
        
        # Only change currency if no journal items exist
        if not journal_items_exist and company.currency_id != tnd_currency:
            company.currency_id = tnd_currency
