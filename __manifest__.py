{
    'name': 'TravelPro - Voyages & Réservations',
    'version': '1.0',
    'category': 'Travel',
    'summary': 'Gestion des sociétés, membres, voyages et réservations',
    'depends': ['base', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/company_views.xml',
        'views/member_views.xml',
        'views/travel_views.xml',
        'views/service_views.xml',
        'views/reservation_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
