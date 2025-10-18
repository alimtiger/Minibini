"""
Tests for PurchaseOrder delete and cancel operations.

Business Rules:
1. Delete PO is only allowed in Draft status
2. Cancel PO is only allowed in Issued status
3. Attempts to delete/cancel in other states should fail
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.purchasing.models import PurchaseOrder
from apps.contacts.models import Business


class PurchaseOrderDeleteTests(TestCase):
    """Test deletion of PurchaseOrders based on status."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create a test business
        self.business = Business.objects.create(
            business_name='Test Vendor',
            our_reference_code='VENDOR001'
        )

    def test_delete_draft_po_shows_confirmation_page(self):
        """Test that GET request to delete a draft PO shows confirmation page."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_delete', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PO-TEST-001')
        self.assertContains(response, 'Are you sure')

    def test_delete_draft_po_succeeds(self):
        """Test that a draft PO can be deleted successfully."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_delete', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect to PO list
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('purchasing:purchase_order_list'))

        # PO should be deleted
        self.assertFalse(PurchaseOrder.objects.filter(po_id=po.po_id).exists())

    def test_delete_issued_po_fails(self):
        """Test that an issued PO cannot be deleted."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_delete', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page (not list)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('purchasing:purchase_order_detail', args=[po.po_id]))

        # PO should still exist
        self.assertTrue(PurchaseOrder.objects.filter(po_id=po.po_id).exists())
        po.refresh_from_db()
        self.assertEqual(po.status, 'issued')

    def test_delete_partly_received_po_fails(self):
        """Test that a partly_received PO cannot be deleted."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'partly_received'
        po.save()

        url = reverse('purchasing:purchase_order_delete', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)

        # PO should still exist
        self.assertTrue(PurchaseOrder.objects.filter(po_id=po.po_id).exists())
        po.refresh_from_db()
        self.assertEqual(po.status, 'partly_received')

    def test_delete_received_in_full_po_fails(self):
        """Test that a received_in_full PO cannot be deleted."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'received_in_full'
        po.save()

        url = reverse('purchasing:purchase_order_delete', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)

        # PO should still exist
        self.assertTrue(PurchaseOrder.objects.filter(po_id=po.po_id).exists())
        po.refresh_from_db()
        self.assertEqual(po.status, 'received_in_full')

    def test_delete_cancelled_po_fails(self):
        """Test that a cancelled PO cannot be deleted."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'cancelled'
        po.save()

        url = reverse('purchasing:purchase_order_delete', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)

        # PO should still exist
        self.assertTrue(PurchaseOrder.objects.filter(po_id=po.po_id).exists())
        po.refresh_from_db()
        self.assertEqual(po.status, 'cancelled')


class PurchaseOrderCancelTests(TestCase):
    """Test cancellation of PurchaseOrders based on status."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create a test business
        self.business = Business.objects.create(
            business_name='Test Vendor',
            our_reference_code='VENDOR001'
        )

    def test_cancel_issued_po_shows_confirmation_page(self):
        """Test that GET request to cancel an issued PO shows confirmation page."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_cancel', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PO-TEST-001')
        self.assertContains(response, 'Are you sure')

    def test_cancel_issued_po_succeeds(self):
        """Test that an issued PO can be cancelled successfully."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_cancel', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect to PO detail page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('purchasing:purchase_order_detail', args=[po.po_id]))

        # PO should be cancelled
        po.refresh_from_db()
        self.assertEqual(po.status, 'cancelled')
        self.assertIsNotNone(po.cancel_date)

    def test_cancel_draft_po_fails(self):
        """Test that a draft PO cannot be cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_cancel', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('purchasing:purchase_order_detail', args=[po.po_id]))

        # PO should still be draft
        po.refresh_from_db()
        self.assertEqual(po.status, 'draft')
        self.assertIsNone(po.cancel_date)

    def test_cancel_partly_received_po_fails(self):
        """Test that a partly_received PO cannot be cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'partly_received'
        po.save()

        url = reverse('purchasing:purchase_order_cancel', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)

        # PO should still be partly_received
        po.refresh_from_db()
        self.assertEqual(po.status, 'partly_received')
        self.assertIsNone(po.cancel_date)

    def test_cancel_received_in_full_po_fails(self):
        """Test that a received_in_full PO cannot be cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'received_in_full'
        po.save()

        url = reverse('purchasing:purchase_order_cancel', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)

        # PO should still be received_in_full
        po.refresh_from_db()
        self.assertEqual(po.status, 'received_in_full')

    def test_cancel_already_cancelled_po_fails(self):
        """Test that a cancelled PO cannot be cancelled again."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'cancelled'
        po.save()

        original_cancel_date = po.cancel_date

        url = reverse('purchasing:purchase_order_cancel', args=[po.po_id])
        response = self.client.post(url)

        # Should redirect back to detail page
        self.assertEqual(response.status_code, 302)

        # PO should still be cancelled with same date
        po.refresh_from_db()
        self.assertEqual(po.status, 'cancelled')
        self.assertEqual(po.cancel_date, original_cancel_date)
