# -*- coding: utf-8 -*-
"""
Migration pour ajouter le champ price_ttc aux lignes de facture existantes
et calculer sa valeur à partir de price_unit
"""

def migrate(cr, version):
    """
    Migration pour le champ price_ttc dans travel.invoice.client.line
    
    Cette migration:
    1. Vérifie si le champ price_ttc existe
    2. Pour toutes les lignes où price_ttc est NULL ou 0:
       - Calcule price_ttc depuis price_unit en inversant la formule
       - Formula inverse: TTC = HT / 0.93 (car HT = TTC * 0.93)
    """
    
    # Vérifier si la colonne price_ttc existe
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='travel_invoice_client_line' 
        AND column_name='price_ttc'
    """)
    
    if cr.fetchone():
        # Le champ existe, on peut faire la migration
        # Pour toutes les lignes où price_ttc est NULL ou 0
        # On calcule price_ttc depuis price_unit
        cr.execute("""
            UPDATE travel_invoice_client_line
            SET price_ttc = CASE 
                WHEN price_unit > 0 THEN price_unit / 0.93
                ELSE 0
            END
            WHERE price_ttc IS NULL OR price_ttc = 0
        """)
        
        print(f"Migration completed: {cr.rowcount} lignes de facture mises à jour")
    else:
        print("Champ price_ttc n'existe pas encore - migration sera exécutée après la mise à jour du module")
