# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle travel.reservation.

Couvre:
- Création de réservation
- Calculs automatiques (nuitées, total, etc.)
- Workflow (confirmation, annulation, crédit)
- Création de facture
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date, timedelta


class TestTravelReservation(TransactionCase):
    """Tests pour le modèle travel.reservation."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()
        
        # Créer une société
        cls.company = cls.env['travel.company'].create({
            'name': 'Test Company',
            'vat': '1111111/A/A/000',
        })
        
        # Créer un membre avec société
        cls.member = cls.env['travel.member'].create({
            'name': 'Test Member',
            'company_id': cls.company.id,
            'email': 'member@test.com',
        })
        
        # Créer un membre sans société
        cls.member_no_company = cls.env['travel.member'].create({
            'name': 'Member No Company',
            'email': 'nocompany@test.com',
        })
        
        # Créer une destination
        cls.destination = cls.env['travel.destination'].create({
            'name': 'Test Destination',
            'price': 500.0,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=7),
        })
        
        # Créer un fournisseur
        cls.supplier = cls.env['res.partner'].create({
            'name': 'Test Supplier',
            'supplier_rank': 1,
        })

    def test_create_reservation(self):
        """Test: Création d'une réservation simple."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=5),
            'price': 500.0,
        })
        
        self.assertTrue(reservation.id)
        self.assertEqual(reservation.status, 'draft')
        self.assertNotEqual(reservation.name, 'Nouveau')

    def test_nights_computation(self):
        """Test: Calcul automatique des nuitées."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date(2024, 1, 1),
            'check_out': date(2024, 1, 6),
            'price': 500.0,
        })
        
        self.assertEqual(reservation.nights, 5)

    def test_participants_computation(self):
        """Test: Calcul automatique du nombre de participants."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'adults': 2,
            'children': 1,
            'infants': 1,
        })
        
        self.assertEqual(reservation.participants, 4)

    def test_total_price_computation(self):
        """Test: Calcul du prix total."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'price': 500.0,
        })
        
        self.assertEqual(reservation.total_price, 500.0)

    def test_create_invoice_without_company(self):
        """Test: Création de facture échoue si membre sans société."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member_no_company.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'price': 500.0,
        })
        
        with self.assertRaises(UserError) as context:
            reservation.action_create_invoice()
        
        self.assertIn('société associée', str(context.exception))

    def test_create_invoice_success(self):
        """Test: Création de facture réussie."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'price': 500.0,
            'status': 'confirmed',
        })
        
        result = reservation.action_create_invoice()
        
        self.assertEqual(result['res_model'], 'travel.invoice.client')
        invoice = self.env['travel.invoice.client'].browse(result['res_id'])
        self.assertTrue(invoice.exists())
        self.assertEqual(invoice.travel_company_id.id, self.company.id)

    def test_cancel_and_credit(self):
        """Test: Annulation avec remboursement crédit."""
        # Vérifier le solde initial
        initial_credit = self.member.credit_balance
        
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'price': 500.0,
            'status': 'confirmed',
        })
        
        reservation.action_cancel_and_credit()
        
        # Vérifier que la réservation est annulée
        self.assertEqual(reservation.status, 'cancel')
        
        # Vérifier que le crédit a été ajouté
        self.member.invalidate_recordset(['credit_balance'])
        self.assertEqual(self.member.credit_balance, initial_credit + 500.0)

    def test_cancel_and_credit_zero_price(self):
        """Test: Annulation avec prix 0 ne crée pas de crédit."""
        initial_credit = self.member.credit_balance
        
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'price': 0.0,
            'status': 'confirmed',
        })
        
        reservation.action_cancel_and_credit()
        
        self.member.invalidate_recordset(['credit_balance'])
        self.assertEqual(self.member.credit_balance, initial_credit)

    def test_workflow_confirm(self):
        """Test: Confirmation de réservation."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
        })
        
        self.assertEqual(reservation.status, 'draft')
        reservation.action_confirm()
        self.assertEqual(reservation.status, 'confirmed')

    def test_workflow_done(self):
        """Test: Marquer réservation comme terminée."""
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'status': 'confirmed',
        })
        
        reservation.action_done()
        self.assertEqual(reservation.status, 'done')

    def test_onchange_destination(self):
        """Test: Onchange destination remplit les champs automatiquement."""
        reservation = self.env['travel.reservation'].new({
            'member_id': self.member.id,
        })
        
        reservation.destination_id = self.destination
        reservation._onchange_destination_id()
        
        self.assertEqual(reservation.price, 500.0)
        self.assertEqual(reservation.check_in, self.destination.start_date)
        self.assertEqual(reservation.check_out, self.destination.end_date)

    def test_supplier_auto_rank(self):
        """Test: Le fournisseur est automatiquement marqué."""
        supplier = self.env['res.partner'].create({
            'name': 'New Supplier',
            'supplier_rank': 0,
        })
        
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': self.destination.id,
            'check_in': date.today(),
            'check_out': date.today() + timedelta(days=3),
            'supplier_id': supplier.id,
        })
        
        self.assertEqual(supplier.supplier_rank, 1)












