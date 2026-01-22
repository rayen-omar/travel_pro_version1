{
    'name': 'TravelPro ERP',
    'version': '16.0.4.1',
    'summary': 'Agence de Voyage - Réservations, Crédit, Caisse, Factures',
    'description': '''
        Module complet de gestion d'agence de voyage:
        
        FONCTIONNALITÉS:
        ================
        - Gestion des sociétés et membres
        - Gestion des fournisseurs et services
        - Réservations et voyages
        - Système de crédit client
        - Facturation clients et fournisseurs
        - Gestion de caisse avec sous-caisses
        - Retenues à la source
        - Rapports et statistiques
        
        SÉCURITÉ:
        =========
        - Groupes: Agent de Voyage, Responsable Agence, Comptable
        - Règles d'accès par groupe et par société
        - Audit trail sur les champs critiques
        
        CHANGELOG v16.0.4.0:
        ====================
        - Ajout des groupes de sécurité
        - Ajout des record rules
        - Ajout des SQL constraints
        - Ajout des validations email/téléphone
        - Corrections des exceptions silencieuses
        - Optimisation des imports
        - Ajout des tests unitaires
        - Documentation complète
    ''',
    'category': 'Sales/Travel',
    'author': 'WE CAN TRAVEL',
    'website': 'https://we-cantravel.com',
    'license': 'OPL-1',
    'depends': [
        'base',
        'sale',
        'account',
        'purchase',
        'point_of_sale',
        'mail',
    ],
    'data': [
        # Sécurité
        'security/ir.model.access.csv',
        # Données
        'data/currency_data.xml',
        'data/sequence_data.xml',
        'data/pos_config.xml',
        'data/cron_data.xml',
        # Vues principales
        'views/company_views.xml',
        'views/member_views.xml',
        'views/supplier_views.xml',
        'views/service_views.xml',
        'views/travel_views.xml',
        'views/reservation_views.xml',
        # Crédit
        'views/credit_views.xml',
        # Facturation
        'views/invoice_client_views.xml',
        'views/report_invoice_client.xml',
        'views/invoice_views.xml',
        'views/invoice_reservations_wizard_views.xml',
        'views/purchase_views.xml',
        'views/purchase_travel_views.xml',
        'views/report_purchase_travel.xml',
        'views/withholding_views.xml',
        # Caisse
        'views/cash_register_views.xml',
        'views/report_cash_receipt.xml',
        # POS
        'views/pos_views.xml',
        # Rapports
        'views/report_reservation_quote.xml',
        # Menu (doit être chargé en dernier)
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'travel_pro_version1/static/src/css/travel_pro_style.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
