"""
Tests for PurchaseOrder status change form on detail view.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.purchasing.models import PurchaseOrder
from apps.contacts.models import Business


class PurchaseOrderStatusFormTests(TestCase):
    """Test the inline status change form on PO detail view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create a test business
        self.business = Business.objects.create(
            business_name='Test Vendor',
            our_reference_code='VENDOR001'
        )

    def test_status_form_shown_for_draft_po(self):
        """Test that status form is shown for draft PO."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update Status')
        self.assertIn('status_form', response.context)

    def test_status_form_shown_for_issued_po(self):
        """Test that status form is shown for issued PO."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update Status')
        self.assertIn('status_form', response.context)

    def test_status_form_not_shown_for_terminal_state(self):
        """Test that status form is not shown for terminal states."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'received_in_full'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Update Status')
        self.assertIsNone(response.context.get('status_form'))

    def test_update_status_from_draft_to_issued(self):
        """Test updating status from draft to issued via form."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.post(url, {
            'update_status': 'true',
            'status': 'issued'
        })

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

        # Check PO status was updated
        po.refresh_from_db()
        self.assertEqual(po.status, 'issued')
        self.assertIsNotNone(po.issued_date)

    def test_update_status_from_issued_to_partly_received(self):
        """Test updating status from issued to partly_received via form."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.post(url, {
            'update_status': 'true',
            'status': 'partly_received'
        })

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)

        # Check PO status was updated
        po.refresh_from_db()
        self.assertEqual(po.status, 'partly_received')

    def test_update_status_from_issued_to_received_in_full(self):
        """Test updating status from issued to received_in_full via form."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.post(url, {
            'update_status': 'true',
            'status': 'received_in_full'
        })

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)

        # Check PO status was updated
        po.refresh_from_db()
        self.assertEqual(po.status, 'received_in_full')
        self.assertIsNotNone(po.received_date)

    def test_update_status_from_issued_to_cancelled(self):
        """Test updating status from issued to cancelled via form."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.post(url, {
            'update_status': 'true',
            'status': 'cancelled'
        })

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)

        # Check PO status was updated
        po.refresh_from_db()
        self.assertEqual(po.status, 'cancelled')
        self.assertIsNotNone(po.cancel_date)

    def test_update_status_invalid_transition_rejected_by_form(self):
        """Test that invalid transition is rejected by form validation."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        # Try to transition directly from draft to partly_received (invalid)
        # This should be rejected because partly_received is not in the dropdown choices for draft
        response = self.client.post(url, {
            'update_status': 'true',
            'status': 'partly_received'
        })

        # Should redirect back (form validation rejects invalid status choice)
        self.assertEqual(response.status_code, 302)

        # Check PO status was NOT updated
        po.refresh_from_db()
        self.assertEqual(po.status, 'draft')

    def test_no_status_change_when_same_status_selected(self):
        """Test that selecting the same status doesn't trigger update."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        original_created_date = po.created_date

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.post(url, {
            'update_status': 'true',
            'status': 'draft'
        })

        # Should redirect without error
        self.assertEqual(response.status_code, 302)

        # Check PO status is still draft and no dates changed
        po.refresh_from_db()
        self.assertEqual(po.status, 'draft')
        self.assertEqual(po.created_date, original_created_date)

    def test_update_status_from_partly_received_to_received_in_full(self):
        """Test updating status from partly_received to received_in_full via form."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'partly_received'
        po.save()

        url = reverse('purchasing:purchase_order_detail', args=[po.po_id])
        response = self.client.post(url, {
            'update_status': 'true',
            'status': 'received_in_full'
        })

        # Should redirect to detail page
        self.assertEqual(response.status_code, 302)

        # Check PO status was updated
        po.refresh_from_db()
        self.assertEqual(po.status, 'received_in_full')
        self.assertIsNotNone(po.received_date)
