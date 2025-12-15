# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle travel.company.

Couvre:
- Création et unicité
- Validation email et matricule fiscal
- Gestion des membres
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestTravelCompany(TransactionCase):
    """Tests pour le modèle travel.company."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()

    def test_create_company(self):
        """Test: Création d'une société simple."""
        company = self.env['travel.company'].create({
            'name': 'Société Test',
            'email': 'contact@societe.com',
            'phone': '+216 71 123 456',
        })
        
        self.assertTrue(company.id)
        self.assertEqual(company.name, 'Société Test')
        self.assertEqual(company.member_count, 0)

    def test_company_name_unique(self):
        """Test: Le nom de société doit être unique."""
        self.env['travel.company'].create({
            'name': 'Unique Company',
        })
        
        with self.assertRaises(Exception):  # IntegrityError
            self.env['travel.company'].create({
                'name': 'Unique Company',  # Duplicate
            })

    def test_vat_unique(self):
        """Test: Le matricule fiscal doit être unique."""
        self.env['travel.company'].create({
            'name': 'Company 1',
            'vat': '1234567/A/M/000',
        })
        
        with self.assertRaises(Exception):  # IntegrityError
            self.env['travel.company'].create({
                'name': 'Company 2',
                'vat': '1234567/A/M/000',  # Duplicate
            })

    def test_email_validation_valid(self):
        """Test: Email valide accepté."""
        company = self.env['travel.company'].create({
            'name': 'Test Email',
            'email': 'valid@domain.com',
        })
        self.assertEqual(company.email, 'valid@domain.com')

    def test_email_validation_invalid(self):
        """Test: Email invalide rejeté."""
        with self.assertRaises(ValidationError):
            self.env['travel.company'].create({
                'name': 'Test Email Invalid',
                'email': 'not-an-email',
            })

    def test_member_count_computation(self):
        """Test: Le compteur de membres est correct."""
        company = self.env['travel.company'].create({
            'name': 'Company With Members',
        })
        
        self.assertEqual(company.member_count, 0)
        
        # Ajouter un membre
        self.env['travel.member'].create({
            'name': 'Member 1',
            'company_id': company.id,
        })
        
        company.invalidate_recordset(['member_count'])
        self.assertEqual(company.member_count, 1)
        
        # Ajouter un autre membre
        self.env['travel.member'].create({
            'name': 'Member 2',
            'company_id': company.id,
        })
        
        company.invalidate_recordset(['member_count'])
        self.assertEqual(company.member_count, 2)

    def test_name_search_by_name(self):
        """Test: Recherche par nom fonctionne."""
        company = self.env['travel.company'].create({
            'name': 'Entreprise ABC',
            'vat': '9999999/A/M/000',
        })
        
        results = self.env['travel.company'].name_search('Entreprise')
        company_ids = [r[0] for r in results]
        self.assertIn(company.id, company_ids)

    def test_name_search_by_vat(self):
        """Test: Recherche par matricule fiscal fonctionne."""
        company = self.env['travel.company'].create({
            'name': 'Company VAT Search',
            'vat': '8888888/B/C/111',
        })
        
        results = self.env['travel.company'].name_search('8888888')
        company_ids = [r[0] for r in results]
        self.assertIn(company.id, company_ids)

    def test_selected_member_ids_sync(self):
        """Test: La synchronisation des membres sélectionnés fonctionne."""
        company = self.env['travel.company'].create({
            'name': 'Company Selection Test',
        })
        
        # Créer des membres sans société
        member1 = self.env['travel.member'].create({
            'name': 'Member Sans Société 1',
        })
        member2 = self.env['travel.member'].create({
            'name': 'Member Sans Société 2',
        })
        
        # Vérifier qu'ils n'ont pas de société
        self.assertFalse(member1.company_id)
        self.assertFalse(member2.company_id)
        
        # Ajouter les membres via selected_member_ids
        company.write({
            'selected_member_ids': [(6, 0, [member1.id, member2.id])]
        })
        
        # Vérifier que les membres sont maintenant liés
        self.assertEqual(member1.company_id.id, company.id)
        self.assertEqual(member2.company_id.id, company.id)
        self.assertEqual(company.member_count, 2)

