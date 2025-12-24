# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle travel.member.

Couvre:
- Création de membre avec/sans partner
- Validation email et téléphone
- Système de crédit
- Recherche par nom/matricule
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestTravelMember(TransactionCase):
    """Tests pour le modèle travel.member."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()
        
        # Créer une société de test
        cls.test_company = cls.env['travel.company'].create({
            'name': 'Société Test',
            'email': 'contact@test.com',
            'vat': '1234567/A/M/000',
        })
        
        # Créer une destination de test
        cls.test_destination = cls.env['travel.destination'].create({
            'name': 'Destination Test',
            'price': 500.0,
        })

    def test_create_member_auto_partner(self):
        """Test: Création d'un membre crée automatiquement un partner."""
        member = self.env['travel.member'].create({
            'name': 'Test Client',
            'email': 'client@test.com',
            'phone': '+216 50 123 456',
        })
        
        self.assertTrue(member.partner_id, "Le partner doit être créé automatiquement")
        self.assertEqual(member.partner_id.name, 'Test Client')
        self.assertEqual(member.partner_id.email, 'client@test.com')
        self.assertEqual(member.partner_id.customer_rank, 1)

    def test_create_member_with_company(self):
        """Test: Création d'un membre avec une société."""
        member = self.env['travel.member'].create({
            'name': 'Employé Test',
            'company_id': self.test_company.id,
        })
        
        self.assertEqual(member.company_id.id, self.test_company.id)
        self.assertIn(member, self.test_company.member_ids)

    def test_email_validation_valid(self):
        """Test: Email valide accepté."""
        member = self.env['travel.member'].create({
            'name': 'Test Email Valid',
            'email': 'valid.email@domain.com',
        })
        self.assertEqual(member.email, 'valid.email@domain.com')

    def test_email_validation_invalid(self):
        """Test: Email invalide rejeté."""
        with self.assertRaises(ValidationError) as context:
            self.env['travel.member'].create({
                'name': 'Test Email Invalid',
                'email': 'invalid-email',
            })
        self.assertIn('Format d\'email invalide', str(context.exception))

    def test_phone_validation_valid(self):
        """Test: Numéro de téléphone valide accepté."""
        member = self.env['travel.member'].create({
            'name': 'Test Phone Valid',
            'phone': '+216 50 123 456',
        })
        self.assertEqual(member.phone, '+216 50 123 456')

    def test_phone_validation_too_short(self):
        """Test: Numéro de téléphone trop court rejeté."""
        with self.assertRaises(ValidationError) as context:
            self.env['travel.member'].create({
                'name': 'Test Phone Short',
                'phone': '123',
            })
        self.assertIn('trop court', str(context.exception))

    def test_matricule_unique(self):
        """Test: Matricule doit être unique."""
        self.env['travel.member'].create({
            'name': 'Member 1',
            'matricule': 'MEM-00001',
        })
        
        with self.assertRaises(Exception):  # IntegrityError wrapped
            self.env['travel.member'].create({
                'name': 'Member 2',
                'matricule': 'MEM-00001',  # Duplicate
            })

    def test_credit_balance_computation(self):
        """Test: Le solde crédit est calculé correctement."""
        member = self.env['travel.member'].create({
            'name': 'Test Credit',
        })
        
        # Solde initial = 0
        self.assertEqual(member.credit_balance, 0.0)
        
        # Ajouter un crédit
        self.env['travel.credit.history'].create({
            'member_id': member.id,
            'amount': 100.0,
            'type': 'recharge',
        })
        
        # Forcer le recalcul
        member.invalidate_recordset(['credit_balance'])
        self.assertEqual(member.credit_balance, 100.0)
        
        # Utiliser du crédit
        self.env['travel.credit.history'].create({
            'member_id': member.id,
            'amount': -30.0,
            'type': 'usage',
        })
        
        member.invalidate_recordset(['credit_balance'])
        self.assertEqual(member.credit_balance, 70.0)

    def test_name_search_by_name(self):
        """Test: Recherche par nom fonctionne."""
        member = self.env['travel.member'].create({
            'name': 'Ahmed Ben Salah',
            'matricule': 'MEM-SEARCH-001',
        })
        
        results = self.env['travel.member'].name_search('Ahmed')
        member_ids = [r[0] for r in results]
        self.assertIn(member.id, member_ids)

    def test_name_search_by_matricule(self):
        """Test: Recherche par matricule fonctionne."""
        member = self.env['travel.member'].create({
            'name': 'Test Search',
            'matricule': 'MEM-UNIQUE-123',
        })
        
        results = self.env['travel.member'].name_search('MEM-UNIQUE')
        member_ids = [r[0] for r in results]
        self.assertIn(member.id, member_ids)

    def test_partner_sync_on_write(self):
        """Test: Le partner est mis à jour quand le membre est modifié."""
        member = self.env['travel.member'].create({
            'name': 'Original Name',
            'email': 'original@test.com',
        })
        
        partner = member.partner_id
        
        # Modifier le membre
        member.write({
            'name': 'Updated Name',
            'email': 'updated@test.com',
        })
        
        # Vérifier que le partner est synchronisé
        self.assertEqual(partner.name, 'Updated Name')
        self.assertEqual(partner.email, 'updated@test.com')

    def test_reservation_count(self):
        """Test: Le compteur de réservations est correct."""
        member = self.env['travel.member'].create({
            'name': 'Test Reservation Count',
        })
        
        self.assertEqual(member.reservation_count, 0)
        
        # Créer une réservation
        self.env['travel.reservation'].create({
            'member_id': member.id,
            'destination_id': self.test_destination.id,
            'check_in': '2024-01-01',
            'check_out': '2024-01-05',
        })
        
        member.invalidate_recordset(['reservation_count'])
        self.assertEqual(member.reservation_count, 1)





