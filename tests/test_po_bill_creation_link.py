"""
Tests for Purchase Order detail page bill creation link visibility.

Business Rules:
1. "Create New Bill for this PO" link should only appear when PO is in issued or later status
2. Link should NOT appear when PO is in draft status
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.purchasing.models import PurchaseOrder
from apps.contacts.models import Business


class PurchaseOrderBillCreationLinkTests(TestCase):
    """Test visibility of bill creation link based on PO status."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create a test business
        self.business = Business.objects.create(
            business_name='Test Vendor',
            our_reference_code='VENDOR001'
        )

    def test_bill_creation_link_hidden_for_draft_po(self):
        """Test that bill creation link is NOT shown for draft POs."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-DRAFT-001',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should NOT contain the "Add Bill" link in Actions section
        self.assertNotContains(response, '>Add Bill</a>')
        self.assertNotContains(response, reverse('purchasing:bill_create_for_po', args=[po.po_id]))

    def test_bill_creation_link_shown_for_issued_po(self):
        """Test that bill creation link IS shown for issued POs."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-ISSUED-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # SHOULD contain the "Add Bill" link in Actions section
        self.assertContains(response, '>Add Bill</a>')
        self.assertContains(response, reverse('purchasing:bill_create_for_po', args=[po.po_id]))

    def test_bill_creation_link_shown_for_partly_received_po(self):
        """Test that bill creation link IS shown for partly_received POs."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-PARTIAL-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'partly_received'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # SHOULD contain the "Add Bill" link
        self.assertContains(response, 'Add Bill')
        self.assertContains(response, reverse('purchasing:bill_create_for_po', args=[po.po_id]))

    def test_bill_creation_link_shown_for_received_in_full_po(self):
        """Test that bill creation link IS shown for received_in_full POs."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-FULL-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'received_in_full'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # SHOULD contain the "Add Bill" link
        self.assertContains(response, 'Add Bill')
        self.assertContains(response, reverse('purchasing:bill_create_for_po', args=[po.po_id]))

    def test_bill_creation_link_not_shown_for_cancelled_po(self):
        """Test that bill creation link isn't shown for cancelled POs."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-CANCEL-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'cancelled'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # should not contain the "Add Bill" link
        self.assertNotContains(response, 'Add Bill')
        self.assertNotContains(response, reverse('purchasing:bill_create_for_po', args=[po.po_id]))

    def test_associated_bills_section_always_shown(self):
        """Test that 'Associated Bills' section header is always shown regardless of status."""
        # Test with draft PO
        draft_po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-DRAFT-002',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_detail', args=[draft_po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should still show "Associated Bills" heading
        self.assertContains(response, 'Associated Bills')

        # Test with issued PO
        issued_po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-ISSUED-002',
            status='draft'
        )
        issued_po.status = 'issued'
        issued_po.save()

        url = reverse('purchasing:purchase_order_detail', args=[issued_po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should still show "Associated Bills" heading
        self.assertContains(response, 'Associated Bills')
