"""
Tests for the PurchaseOrder status state machine.

Business Rules:
1. PO starts in 'draft' status
2. Valid transitions:
   - draft -> issued
   - issued -> partly_received
   - issued -> received_in_full
   - issued -> cancelled
   - partly_received -> received_in_full
3. Terminal states: received_in_full, cancelled
4. Date fields are automatically set on state transitions and are immutable
5. requested_date can be set by user and is editable
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.purchasing.models import PurchaseOrder
from apps.contacts.models import Business
from datetime import timedelta


class PurchaseOrderStatusTransitionTest(TestCase):
    """Test the status state machine for PurchaseOrder."""

    def setUp(self):
        """Set up test data."""
        # Create a test business
        self.business = Business.objects.create(
            business_name='Test Vendor',
            our_reference_code='VENDOR001'
        )

    def test_po_default_status_is_draft(self):
        """Test that a new PO starts in draft status."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001'
        )
        self.assertEqual(po.status, 'draft')

    def test_po_created_date_is_set_automatically(self):
        """Test that created_date is automatically set on creation."""
        before_creation = timezone.now()
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001'
        )
        after_creation = timezone.now()

        self.assertIsNotNone(po.created_date)
        self.assertGreaterEqual(po.created_date, before_creation)
        self.assertLessEqual(po.created_date, after_creation)

    def test_transition_draft_to_issued(self):
        """Test valid transition from draft to issued."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        po.status = 'issued'
        po.save()

        po.refresh_from_db()
        self.assertEqual(po.status, 'issued')
        self.assertIsNotNone(po.issued_date)

    def test_issued_date_set_automatically(self):
        """Test that issued_date is automatically set when transitioning to issued."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        self.assertIsNone(po.issued_date)

        before_transition = timezone.now()
        po.status = 'issued'
        po.save()
        after_transition = timezone.now()

        po.refresh_from_db()
        self.assertIsNotNone(po.issued_date)
        self.assertGreaterEqual(po.issued_date, before_transition)
        self.assertLessEqual(po.issued_date, after_transition)

    def test_transition_issued_to_partly_received(self):
        """Test valid transition from issued to partly_received."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        po.status = 'partly_received'
        po.save()

        po.refresh_from_db()
        self.assertEqual(po.status, 'partly_received')

    def test_transition_issued_to_received_in_full(self):
        """Test valid transition from issued to received_in_full."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        po.status = 'received_in_full'
        po.save()

        po.refresh_from_db()
        self.assertEqual(po.status, 'received_in_full')
        self.assertIsNotNone(po.received_date)

    def test_transition_issued_to_cancelled(self):
        """Test valid transition from issued to cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        po.status = 'cancelled'
        po.save()

        po.refresh_from_db()
        self.assertEqual(po.status, 'cancelled')
        self.assertIsNotNone(po.cancel_date)

    def test_transition_partly_received_to_received_in_full(self):
        """Test valid transition from partly_received to received_in_full."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'partly_received'
        po.save()

        po.status = 'received_in_full'
        po.save()

        po.refresh_from_db()
        self.assertEqual(po.status, 'received_in_full')
        self.assertIsNotNone(po.received_date)

    def test_received_date_set_automatically(self):
        """Test that received_date is automatically set when transitioning to received_in_full."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        self.assertIsNone(po.received_date)

        before_transition = timezone.now()
        po.status = 'received_in_full'
        po.save()
        after_transition = timezone.now()

        po.refresh_from_db()
        self.assertIsNotNone(po.received_date)
        self.assertGreaterEqual(po.received_date, before_transition)
        self.assertLessEqual(po.received_date, after_transition)

    def test_cancel_date_set_automatically(self):
        """Test that cancel_date is automatically set when transitioning to cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        self.assertIsNone(po.cancel_date)

        before_transition = timezone.now()
        po.status = 'cancelled'
        po.save()
        after_transition = timezone.now()

        po.refresh_from_db()
        self.assertIsNotNone(po.cancel_date)
        self.assertGreaterEqual(po.cancel_date, before_transition)
        self.assertLessEqual(po.cancel_date, after_transition)

    def test_invalid_transition_draft_to_partly_received(self):
        """Test that draft cannot transition to partly_received."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        po.status = 'partly_received'
        with self.assertRaises(ValidationError) as context:
            po.save()

        self.assertIn('cannot transition', str(context.exception).lower())

    def test_invalid_transition_draft_to_received_in_full(self):
        """Test that draft cannot transition to received_in_full."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        po.status = 'received_in_full'
        with self.assertRaises(ValidationError) as context:
            po.save()

        self.assertIn('cannot transition', str(context.exception).lower())

    def test_invalid_transition_draft_to_cancelled(self):
        """Test that draft cannot transition to cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        po.status = 'cancelled'
        with self.assertRaises(ValidationError) as context:
            po.save()

        self.assertIn('cannot transition', str(context.exception).lower())

    def test_invalid_transition_partly_received_to_cancelled(self):
        """Test that partly_received cannot transition to cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'partly_received'
        po.save()

        po.status = 'cancelled'
        with self.assertRaises(ValidationError) as context:
            po.save()

        self.assertIn('cannot transition', str(context.exception).lower())

    def test_terminal_state_received_in_full_cannot_transition(self):
        """Test that received_in_full is a terminal state."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'received_in_full'
        po.save()

        # Try to transition to any other state
        po.status = 'cancelled'
        with self.assertRaises(ValidationError) as context:
            po.save()

        self.assertIn('terminal state', str(context.exception).lower())

    def test_terminal_state_cancelled_cannot_transition(self):
        """Test that cancelled is a terminal state."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'cancelled'
        po.save()

        # Try to transition to any other state
        po.status = 'received_in_full'
        with self.assertRaises(ValidationError) as context:
            po.save()

        self.assertIn('terminal state', str(context.exception).lower())

    def test_created_date_is_immutable(self):
        """Test that created_date cannot be changed after creation."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001'
        )
        original_created_date = po.created_date

        # Try to change created_date
        new_date = timezone.now() + timedelta(days=1)
        po.created_date = new_date
        po.save()

        po.refresh_from_db()
        # Should be reset to original value
        self.assertEqual(po.created_date, original_created_date)

    def test_issued_date_is_immutable(self):
        """Test that issued_date cannot be changed after being set."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        original_issued_date = po.issued_date

        # Try to change issued_date
        new_date = timezone.now() + timedelta(days=1)
        po.issued_date = new_date
        po.save()

        po.refresh_from_db()
        # Should be reset to original value
        self.assertEqual(po.issued_date, original_issued_date)

    def test_received_date_is_immutable(self):
        """Test that received_date cannot be changed after being set."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'received_in_full'
        po.save()

        original_received_date = po.received_date

        # Try to change received_date
        new_date = timezone.now() + timedelta(days=1)
        po.received_date = new_date
        po.save()

        po.refresh_from_db()
        # Should be reset to original value
        self.assertEqual(po.received_date, original_received_date)

    def test_cancel_date_is_immutable(self):
        """Test that cancel_date cannot be changed after being set."""
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

        # Try to change cancel_date
        new_date = timezone.now() + timedelta(days=1)
        po.cancel_date = new_date
        po.save()

        po.refresh_from_db()
        # Should be reset to original value
        self.assertEqual(po.cancel_date, original_cancel_date)

    def test_requested_date_is_optional_and_editable(self):
        """Test that requested_date is optional and can be edited."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001'
        )

        # Should be None initially
        self.assertIsNone(po.requested_date)

        # Can be set
        requested_date = timezone.now() + timedelta(days=7)
        po.requested_date = requested_date
        po.save()

        po.refresh_from_db()
        self.assertEqual(po.requested_date, requested_date)

        # Can be changed
        new_requested_date = timezone.now() + timedelta(days=14)
        po.requested_date = new_requested_date
        po.save()

        po.refresh_from_db()
        self.assertEqual(po.requested_date, new_requested_date)

    def test_all_valid_paths_draft_issued_partly_received_full(self):
        """Test the full path: draft -> issued -> partly_received -> received_in_full."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        po.status = 'issued'
        po.save()
        self.assertEqual(po.status, 'issued')

        po.status = 'partly_received'
        po.save()
        self.assertEqual(po.status, 'partly_received')

        po.status = 'received_in_full'
        po.save()
        self.assertEqual(po.status, 'received_in_full')

    def test_all_valid_paths_draft_issued_full(self):
        """Test the path: draft -> issued -> received_in_full."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        po.status = 'issued'
        po.save()
        self.assertEqual(po.status, 'issued')

        po.status = 'received_in_full'
        po.save()
        self.assertEqual(po.status, 'received_in_full')

    def test_all_valid_paths_draft_issued_cancelled(self):
        """Test the path: draft -> issued -> cancelled."""
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number='PO-TEST-001',
            status='draft'
        )

        po.status = 'issued'
        po.save()
        self.assertEqual(po.status, 'issued')

        po.status = 'cancelled'
        po.save()
        self.assertEqual(po.status, 'cancelled')
