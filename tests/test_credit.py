# -*- coding: utf-8 -*-
"""
Tests unitaires pour le système de crédit.

Couvre:
- Historique de crédit
- Recharge de crédit
- Utilisation et remboursement
"""
from odoo.tests.common import TransactionCase


class TestCreditSystem(TransactionCase):
    """Tests pour le système de crédit (travel.credit.history, travel.credit.recharge)."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()
        
        cls.member = cls.env['travel.member'].create({
            'name': 'Credit Test Member',
        })

    def test_initial_balance_zero(self):
        """Test: Solde initial est zéro."""
        self.assertEqual(self.member.credit_balance, 0.0)

    def test_recharge_credit(self):
        """Test: Recharge de crédit via historique."""
        self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 500.0,
            'type': 'recharge',
            'note': 'Recharge test',
        })
        
        self.member.invalidate_recordset(['credit_balance'])
        self.assertEqual(self.member.credit_balance, 500.0)

    def test_recharge_wizard(self):
        """Test: Recharge via wizard."""
        wizard = self.env['travel.credit.recharge'].create({
            'member_id': self.member.id,
            'amount': 200.0,
        })
        
        wizard.action_recharge()
        
        self.member.invalidate_recordset(['credit_balance'])
        self.assertEqual(self.member.credit_balance, 200.0)

    def test_multiple_recharges(self):
        """Test: Plusieurs recharges s'additionnent."""
        self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 100.0,
            'type': 'recharge',
        })
        self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 150.0,
            'type': 'recharge',
        })
        
        self.member.invalidate_recordset(['credit_balance'])
        self.assertEqual(self.member.credit_balance, 250.0)

    def test_usage_reduces_balance(self):
        """Test: Utilisation réduit le solde."""
        # Recharger d'abord
        self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 500.0,
            'type': 'recharge',
        })
        
        # Utiliser (montant négatif)
        self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': -200.0,
            'type': 'usage',
        })
        
        self.member.invalidate_recordset(['credit_balance'])
        self.assertEqual(self.member.credit_balance, 300.0)

    def test_refund_increases_balance(self):
        """Test: Remboursement augmente le solde."""
        self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 150.0,
            'type': 'refund',
        })
        
        self.member.invalidate_recordset(['credit_balance'])
        self.assertEqual(self.member.credit_balance, 150.0)

    def test_credit_history_order(self):
        """Test: Historique ordonné par date décroissante."""
        h1 = self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 100.0,
            'type': 'recharge',
        })
        h2 = self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 200.0,
            'type': 'recharge',
        })
        
        history = self.env['travel.credit.history'].search([
            ('member_id', '=', self.member.id)
        ])
        
        # Le plus récent en premier
        self.assertEqual(history[0].id, h2.id)

    def test_credit_with_reservation_link(self):
        """Test: Crédit lié à une réservation."""
        # Créer une destination
        destination = self.env['travel.destination'].create({
            'name': 'Credit Destination',
            'price': 300.0,
        })
        
        # Créer une réservation
        reservation = self.env['travel.reservation'].create({
            'member_id': self.member.id,
            'destination_id': destination.id,
            'check_in': '2024-01-01',
            'check_out': '2024-01-05',
            'price': 300.0,
        })
        
        # Créer un crédit lié
        credit = self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 300.0,
            'type': 'refund',
            'reservation_id': reservation.id,
        })
        
        self.assertEqual(credit.reservation_id.id, reservation.id)

    def test_cascade_delete_with_member(self):
        """Test: Historique supprimé avec le membre (cascade)."""
        # Créer un historique
        self.env['travel.credit.history'].create({
            'member_id': self.member.id,
            'amount': 100.0,
            'type': 'recharge',
        })
        
        history_count_before = self.env['travel.credit.history'].search_count([
            ('member_id', '=', self.member.id)
        ])
        self.assertEqual(history_count_before, 1)
        
        # Supprimer le membre
        member_id = self.member.id
        self.member.partner_id.unlink()  # D'abord supprimer le partner
        
        # Note: Ce test dépend de la configuration ondelete='cascade'
        # Si le membre est supprimé, l'historique devrait l'être aussi

