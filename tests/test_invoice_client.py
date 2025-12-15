# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle travel.invoice.client.

Couvre:
- Création de facture
- Calculs TVA, HT, TTC
- Remises
- Retenues à la source
- Workflow
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestTravelInvoiceClient(TransactionCase):
    """Tests pour le modèle travel.invoice.client."""

    @classmethod
    def setUpClass(cls):
        """Préparer les données de test."""
        super().setUpClass()
        
        # Créer une société
        cls.company = cls.env['travel.company'].create({
            'name': 'Invoice Test Company',
            'vat': '2222222/A/A/000',
        })
        
        # Créer un membre
        cls.member = cls.env['travel.member'].create({
            'name': 'Invoice Test Member',
            'company_id': cls.company.id,
        })
        
        # Créer une destination
        cls.destination = cls.env['travel.destination'].create({
            'name': 'Invoice Test Destination',
            'price': 1000.0,
        })

    def test_create_invoice(self):
        """Test: Création d'une facture simple."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
        })
        
        self.assertTrue(invoice.id)
        self.assertNotEqual(invoice.name, 'Nouveau')
        self.assertEqual(invoice.state, 'draft')

    def test_amount_computation_7_percent(self):
        """Test: Calcul correct avec TVA 7%."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Line',
                'quantity': 1.0,
                'price_ttc': 1070.0,  # TTC
                'tax_rate': '7',
            })],
        })
        
        # HT = 1070 / 1.07 = 1000
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)
        # TVA = 1000 * 0.07 = 70
        self.assertAlmostEqual(invoice.amount_tax, 70.0, places=2)
        # Total = 1000 + 70 + 1 (timbre) = 1071
        self.assertAlmostEqual(invoice.amount_total, 1071.0, places=2)

    def test_amount_computation_19_percent(self):
        """Test: Calcul correct avec TVA 19%."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Line 19%',
                'quantity': 1.0,
                'price_ttc': 1190.0,  # TTC
                'tax_rate': '19',
            })],
        })
        
        # HT = 1190 / 1.19 = 1000
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)
        # TVA = 1000 * 0.19 = 190
        self.assertAlmostEqual(invoice.amount_tax, 190.0, places=2)

    def test_discount_percent(self):
        """Test: Calcul avec remise en pourcentage."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'discount_type': 'percent',
            'discount_rate': 10.0,  # 10%
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Discount',
                'quantity': 1.0,
                'price_ttc': 1070.0,
                'tax_rate': '7',
            })],
        })
        
        # HT avant remise = 1000
        # Remise = 1000 * 10% = 100
        self.assertAlmostEqual(invoice.discount_amount, 100.0, places=2)
        # HT après remise = 900
        self.assertAlmostEqual(invoice.amount_after_discount, 900.0, places=2)

    def test_discount_fixed(self):
        """Test: Calcul avec remise fixe."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'discount_type': 'fixed',
            'discount_fixed': 50.0,
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Fixed Discount',
                'quantity': 1.0,
                'price_ttc': 1070.0,
                'tax_rate': '7',
            })],
        })
        
        self.assertAlmostEqual(invoice.discount_amount, 50.0, places=2)
        # HT après remise = 1000 - 50 = 950
        self.assertAlmostEqual(invoice.amount_after_discount, 950.0, places=2)

    def test_withholding_tax_1_percent(self):
        """Test: Calcul retenue 1%."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'apply_withholding_tax': True,
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Withholding',
                'quantity': 1.0,
                'price_ttc': 1070.0,
                'tax_rate': '7',
            })],
        })
        
        # Total = 1071 (avec timbre)
        # Retenue 1% sur (1071 - 1) = 10.70
        self.assertAlmostEqual(invoice.withholding_tax_amount, 10.70, places=2)

    def test_vat_withholding_25_percent(self):
        """Test: Calcul retenue 25% TVA."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'apply_vat_withholding': True,
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test VAT Withholding',
                'quantity': 1.0,
                'price_ttc': 1070.0,
                'tax_rate': '7',
            })],
        })
        
        # TVA = 70
        # Retenue 25% TVA = 70 * 0.25 = 17.50
        self.assertAlmostEqual(invoice.vat_withholding_amount, 17.50, places=2)

    def test_net_to_pay(self):
        """Test: Calcul net à payer avec retenues."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'apply_withholding_tax': True,
            'apply_vat_withholding': True,
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Net',
                'quantity': 1.0,
                'price_ttc': 1070.0,
                'tax_rate': '7',
            })],
        })
        
        # Total = 1071
        # Retenues = 10.70 + 17.50 = 28.20
        # Net = 1071 - 28.20 = 1042.80
        expected_net = invoice.amount_total - invoice.total_withholding
        self.assertAlmostEqual(invoice.net_to_pay, expected_net, places=2)

    def test_confirm_without_lines(self):
        """Test: Confirmation échoue sans lignes."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
        })
        
        with self.assertRaises(UserError) as context:
            invoice.action_confirm()
        
        self.assertIn('ligne', str(context.exception).lower())

    def test_workflow_confirm(self):
        """Test: Confirmation de facture."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Confirm',
                'quantity': 1.0,
                'price_ttc': 100.0,
                'tax_rate': '7',
            })],
        })
        
        invoice.action_confirm()
        self.assertEqual(invoice.state, 'confirmed')

    def test_workflow_paid(self):
        """Test: Marquer facture comme payée."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'state': 'confirmed',
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Paid',
                'quantity': 1.0,
                'price_ttc': 100.0,
                'tax_rate': '7',
            })],
        })
        
        invoice.action_set_paid()
        self.assertEqual(invoice.state, 'paid')

    def test_amount_in_words(self):
        """Test: Montant en lettres est généré."""
        invoice = self.env['travel.invoice.client'].create({
            'travel_company_id': self.company.id,
            'member_ids': [(6, 0, [self.member.id])],
            'invoice_line_ids': [(0, 0, {
                'passenger_id': self.member.id,
                'description': 'Test Words',
                'quantity': 1.0,
                'price_ttc': 100.0,
                'tax_rate': '7',
            })],
        })
        
        self.assertTrue(invoice.amount_in_words_fr)
        self.assertIn('Dinars', invoice.amount_in_words_fr)

