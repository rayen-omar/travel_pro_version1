# -*- coding: utf-8 -*-
"""
Tests unitaires pour les modèles cash.register et cash.register.operation.

Couvre:
- Gestion des caisses (ouverture/fermeture)
- Hiérarchie caisse principale / sous-caisses
- Opérations de caisse
- Calculs de solde
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestCashRegister(TransactionCase):
    """Tests pour le modèle cash.register."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()
        
        # Créer une caisse principale
        cls.main_cash = cls.env['cash.register'].create({
            'name': 'Caisse Principale Test',
            'code': 'MAIN-TEST',
            'is_main': True,
            'user_id': cls.env.user.id,
        })

    def test_create_main_cash(self):
        """Test: Création d'une caisse principale."""
        self.assertTrue(self.main_cash.id)
        self.assertTrue(self.main_cash.is_main)
        self.assertEqual(self.main_cash.state, 'closed')

    def test_create_sub_cash(self):
        """Test: Création d'une sous-caisse."""
        sub_cash = self.env['cash.register'].create({
            'name': 'Sous-Caisse Test',
            'code': 'SUB-TEST-1',
            'is_main': False,
            'main_cash_id': self.main_cash.id,
            'user_id': self.env.user.id,
        })
        
        self.assertFalse(sub_cash.is_main)
        self.assertEqual(sub_cash.main_cash_id.id, self.main_cash.id)

    def test_sub_cash_without_main_fails(self):
        """Test: Sous-caisse sans parent échoue."""
        with self.assertRaises(ValidationError):
            self.env['cash.register'].create({
                'name': 'Invalid Sub Cash',
                'code': 'INVALID-SUB',
                'is_main': False,
                'main_cash_id': False,  # Pas de parent
                'user_id': self.env.user.id,
            })

    def test_main_cash_with_parent_fails(self):
        """Test: Caisse principale avec parent échoue."""
        with self.assertRaises(ValidationError):
            self.env['cash.register'].create({
                'name': 'Invalid Main',
                'code': 'INVALID-MAIN',
                'is_main': True,
                'main_cash_id': self.main_cash.id,  # Parent invalide
                'user_id': self.env.user.id,
            })

    def test_only_one_main_per_company(self):
        """Test: Une seule caisse principale par société."""
        with self.assertRaises(ValidationError):
            self.env['cash.register'].create({
                'name': 'Second Main Cash',
                'code': 'MAIN-2',
                'is_main': True,
                'user_id': self.env.user.id,
            })

    def test_max_two_sub_cashes(self):
        """Test: Maximum 2 sous-caisses par caisse principale."""
        # Créer 2 sous-caisses
        self.env['cash.register'].create({
            'name': 'Sub 1',
            'code': 'SUB-1',
            'is_main': False,
            'main_cash_id': self.main_cash.id,
            'user_id': self.env.user.id,
        })
        self.env['cash.register'].create({
            'name': 'Sub 2',
            'code': 'SUB-2',
            'is_main': False,
            'main_cash_id': self.main_cash.id,
            'user_id': self.env.user.id,
        })
        
        # La 3ème doit échouer
        with self.assertRaises(ValidationError):
            self.env['cash.register'].create({
                'name': 'Sub 3',
                'code': 'SUB-3',
                'is_main': False,
                'main_cash_id': self.main_cash.id,
                'user_id': self.env.user.id,
            })

    def test_code_unique(self):
        """Test: Code de caisse unique."""
        with self.assertRaises(ValidationError):
            self.env['cash.register'].create({
                'name': 'Duplicate Code',
                'code': 'MAIN-TEST',  # Duplicate
                'is_main': False,
                'main_cash_id': self.main_cash.id,
                'user_id': self.env.user.id,
            })

    def test_open_main_cash(self):
        """Test: Ouverture de caisse principale."""
        self.main_cash.action_open_cash()
        
        self.assertEqual(self.main_cash.state, 'opened')
        self.assertTrue(self.main_cash.opening_date)
        self.assertEqual(self.main_cash.opening_user_id.id, self.env.user.id)

    def test_open_sub_cash_requires_main_open(self):
        """Test: Ouverture sous-caisse nécessite principale ouverte."""
        sub_cash = self.env['cash.register'].create({
            'name': 'Sub Cash Open Test',
            'code': 'SUB-OPEN',
            'is_main': False,
            'main_cash_id': self.main_cash.id,
            'user_id': self.env.user.id,
        })
        
        # Principale fermée - doit échouer
        with self.assertRaises(UserError):
            sub_cash.action_open_cash()
        
        # Ouvrir la principale
        self.main_cash.action_open_cash()
        
        # Maintenant ça doit marcher
        sub_cash.action_open_cash()
        self.assertEqual(sub_cash.state, 'opened')

    def test_close_main_requires_sub_closed(self):
        """Test: Fermeture principale nécessite sous-caisses fermées."""
        sub_cash = self.env['cash.register'].create({
            'name': 'Sub Cash Close Test',
            'code': 'SUB-CLOSE',
            'is_main': False,
            'main_cash_id': self.main_cash.id,
            'user_id': self.env.user.id,
        })
        
        # Ouvrir les deux
        self.main_cash.action_open_cash()
        sub_cash.action_open_cash()
        
        # Fermer la principale doit échouer
        with self.assertRaises(UserError):
            self.main_cash.action_close_cash()
        
        # Fermer la sous-caisse d'abord
        sub_cash.action_close_sub_cash()
        
        # Maintenant fermer la principale
        self.main_cash.action_close_cash()
        self.assertEqual(self.main_cash.state, 'closed')

    def test_balance_computation(self):
        """Test: Calcul du solde de caisse."""
        self.main_cash.action_open_cash()
        
        # Créer des opérations
        self.env['cash.register.operation'].create({
            'cash_register_id': self.main_cash.id,
            'type': 'receipt',
            'amount': 500.0,
            'payment_method': 'cash',
            'state': 'confirmed',
        })
        
        self.env['cash.register.operation'].create({
            'cash_register_id': self.main_cash.id,
            'type': 'expense',
            'amount': 100.0,
            'payment_method': 'cash',
            'state': 'confirmed',
        })
        
        self.main_cash.invalidate_recordset(['total_receipts', 'total_expenses', 'balance'])
        
        self.assertEqual(self.main_cash.total_receipts, 500.0)
        self.assertEqual(self.main_cash.total_expenses, 100.0)
        self.assertEqual(self.main_cash.balance, 400.0)


class TestCashRegisterOperation(TransactionCase):
    """Tests pour le modèle cash.register.operation."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()
        
        cls.main_cash = cls.env['cash.register'].create({
            'name': 'Operation Test Cash',
            'code': 'OP-TEST',
            'is_main': True,
            'user_id': cls.env.user.id,
        })
        cls.main_cash.action_open_cash()

    def test_create_operation(self):
        """Test: Création d'une opération."""
        operation = self.env['cash.register.operation'].create({
            'cash_register_id': self.main_cash.id,
            'type': 'receipt',
            'amount': 100.0,
            'payment_method': 'cash',
        })
        
        self.assertTrue(operation.id)
        self.assertNotEqual(operation.name, 'Nouveau')
        self.assertEqual(operation.state, 'draft')

    def test_amount_positive_required(self):
        """Test: Montant doit être positif."""
        with self.assertRaises(ValidationError):
            self.env['cash.register.operation'].create({
                'cash_register_id': self.main_cash.id,
                'type': 'receipt',
                'amount': 0.0,
                'payment_method': 'cash',
            })
        
        with self.assertRaises(ValidationError):
            self.env['cash.register.operation'].create({
                'cash_register_id': self.main_cash.id,
                'type': 'receipt',
                'amount': -50.0,
                'payment_method': 'cash',
            })

    def test_confirm_operation(self):
        """Test: Confirmation d'opération."""
        operation = self.env['cash.register.operation'].create({
            'cash_register_id': self.main_cash.id,
            'type': 'receipt',
            'amount': 100.0,
            'payment_method': 'cash',
        })
        
        operation.action_confirm()
        self.assertEqual(operation.state, 'confirmed')

    def test_confirm_requires_open_cash(self):
        """Test: Confirmation nécessite caisse ouverte."""
        # Fermer la caisse
        self.main_cash.action_close_cash()
        
        operation = self.env['cash.register.operation'].create({
            'cash_register_id': self.main_cash.id,
            'type': 'receipt',
            'amount': 100.0,
            'payment_method': 'cash',
        })
        
        with self.assertRaises(UserError):
            operation.action_confirm()

    def test_cancel_operation(self):
        """Test: Annulation d'opération."""
        operation = self.env['cash.register.operation'].create({
            'cash_register_id': self.main_cash.id,
            'type': 'receipt',
            'amount': 100.0,
            'payment_method': 'cash',
            'state': 'confirmed',
        })
        
        operation.action_cancel()
        self.assertEqual(operation.state, 'cancelled')




