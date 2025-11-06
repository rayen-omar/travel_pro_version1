#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour nettoyer les références aux anciens champs purchase_amount et sale_amount
dans les vues personnalisées de la base de données.
"""

import xml.etree.ElementTree as ET
from odoo import api, SUPERUSER_ID

def cleanup_views(env):
    """Supprime les références à purchase_amount et sale_amount dans les vues"""
    
    # Trouver toutes les vues pour travel.reservation
    views = env['ir.ui.view'].search([
        ('model', '=', 'travel.reservation')
    ])
    
    updated_count = 0
    for view in views:
        arch = view.arch_db or view.arch
        if not arch:
            continue
        
        # Vérifier si la vue contient les anciens champs
        if 'purchase_amount' in arch or 'sale_amount' in arch:
            try:
                # Parser le XML
                root = ET.fromstring(arch)
                
                # Supprimer les champs purchase_amount et sale_amount
                for field in root.findall(".//field[@name='purchase_amount']"):
                    parent = field.getparent()
                    if parent is not None:
                        parent.remove(field)
                
                for field in root.findall(".//field[@name='sale_amount']"):
                    parent = field.getparent()
                    if parent is not None:
                        parent.remove(field)
                
                # Reconstruire le XML
                new_arch = ET.tostring(root, encoding='unicode')
                
                # Mettre à jour la vue
                view.write({'arch_db': new_arch})
                updated_count += 1
                print(f"✓ Vue '{view.name}' mise à jour (ID: {view.id})")
                
            except Exception as e:
                print(f"✗ Erreur lors de la mise à jour de la vue '{view.name}': {e}")
    
    print(f"\n✅ {updated_count} vue(s) mise(s) à jour")
    
    # Invalider le cache
    env['ir.ui.view'].clear_caches()
    print("✅ Cache des vues invalidé")

if __name__ == '__main__':
    # Pour exécuter via odoo-bin shell:
    # python odoo-bin shell -d votre_db
    # Puis:
    # exec(open('addons/travel_pro_version1/scripts/cleanup_old_fields.py').read())
    # cleanup_views(env)
    pass


