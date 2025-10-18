"""
Tests for Bill creation with Purchase Order status validation.

Business Rules:
1. Bills can only be created from POs that are in 'issued' or later status
2. Bills cannot be created from draft POs
3. Bills can be created without a PO (purchase_order=None)
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.purchasing.models import Bill, PurchaseOrder
from apps.contacts.models import Contact


class BillPurchaseOrderStatusValidationTest(TestCase):
    """Test that Bills can only be created from issued or later POs."""

    def setUp(self):
        """Set up test data."""
        # Create a test contact
        self.contact = Contact.objects.create(
            name='Test Vendor'
        )

    def test_bill_creation_without_po_succeeds(self):
        """Test that a Bill can be created without a Purchase Order."""
        bill = Bill.objects.create(
            purchase_order=None,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )
        self.assertIsNone(bill.purchase_order)
        self.assertEqual(bill.vendor_invoice_number, 'INV-001')

    def test_bill_creation_with_draft_po_fails(self):
        """Test that a Bill cannot be created from a draft PO."""
        po = PurchaseOrder.objects.create(
            po_number='PO-TEST-001',
            status='draft'
        )

        bill = Bill(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        with self.assertRaises(ValidationError) as context:
            bill.full_clean()

        self.assertIn('issued or later status', str(context.exception).lower())

    def test_bill_creation_with_issued_po_succeeds(self):
        """Test that a Bill can be created from an issued PO."""
        po = PurchaseOrder.objects.create(
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        bill = Bill.objects.create(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        self.assertEqual(bill.purchase_order, po)
        self.assertEqual(bill.vendor_invoice_number, 'INV-001')

    def test_bill_creation_with_partly_received_po_succeeds(self):
        """Test that a Bill can be created from a partly_received PO."""
        po = PurchaseOrder.objects.create(
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'partly_received'
        po.save()

        bill = Bill.objects.create(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        self.assertEqual(bill.purchase_order, po)
        self.assertEqual(bill.vendor_invoice_number, 'INV-001')

    def test_bill_creation_with_received_in_full_po_succeeds(self):
        """Test that a Bill can be created from a received_in_full PO."""
        po = PurchaseOrder.objects.create(
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'received_in_full'
        po.save()

        bill = Bill.objects.create(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        self.assertEqual(bill.purchase_order, po)
        self.assertEqual(bill.vendor_invoice_number, 'INV-001')

    def test_bill_creation_with_cancelled_po_succeeds(self):
        """Test that a Bill can be created from a cancelled PO."""
        po = PurchaseOrder.objects.create(
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()
        po.status = 'cancelled'
        po.save()

        bill = Bill.objects.create(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        self.assertEqual(bill.purchase_order, po)
        self.assertEqual(bill.vendor_invoice_number, 'INV-001')

    def test_bill_update_to_draft_po_fails(self):
        """Test that an existing Bill cannot be updated to reference a draft PO."""
        # Create bill without PO
        bill = Bill.objects.create(
            purchase_order=None,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        # Create a draft PO
        po = PurchaseOrder.objects.create(
            po_number='PO-TEST-001',
            status='draft'
        )

        # Try to update bill to reference the draft PO
        bill.purchase_order = po

        with self.assertRaises(ValidationError) as context:
            bill.full_clean()

        self.assertIn('issued or later status', str(context.exception).lower())

    def test_bill_update_from_issued_to_draft_po_fails(self):
        """Test that a Bill cannot be updated to reference a draft PO even if it previously had an issued PO."""
        # Create an issued PO
        issued_po = PurchaseOrder.objects.create(
            po_number='PO-ISSUED-001',
            status='draft'
        )
        issued_po.status = 'issued'
        issued_po.save()

        # Create bill with issued PO
        bill = Bill.objects.create(
            purchase_order=issued_po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        # Create a draft PO
        draft_po = PurchaseOrder.objects.create(
            po_number='PO-DRAFT-001',
            status='draft'
        )

        # Try to update bill to reference the draft PO
        bill.purchase_order = draft_po

        with self.assertRaises(ValidationError) as context:
            bill.full_clean()

        self.assertIn('issued or later status', str(context.exception).lower())

    def test_bill_update_to_none_succeeds(self):
        """Test that a Bill can be updated to have no PO."""
        # Create an issued PO
        po = PurchaseOrder.objects.create(
            po_number='PO-TEST-001',
            status='draft'
        )
        po.status = 'issued'
        po.save()

        # Create bill with PO
        bill = Bill.objects.create(
            purchase_order=po,
            contact=self.contact,
            vendor_invoice_number='INV-001'
        )

        # Update bill to remove PO
        bill.purchase_order = None
        bill.save()

        bill.refresh_from_db()
        self.assertIsNone(bill.purchase_order)
