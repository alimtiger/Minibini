from django.test import TestCase
from apps.purchasing.models import Bill, PurchaseOrder
from apps.contacts.models import Contact, Business


class BillBusinessAutoAssociationTest(TestCase):
    """
    Test that Bill automatically associates Business from Contact on creation.
    """

    def setUp(self):
        """Set up test data with businesses and contacts."""
        # Create businesses
        self.business1 = Business.objects.create(business_name="Vendor Corp")
        self.business2 = Business.objects.create(business_name="Alternative Vendor Inc")

        # Create contact with business
        self.contact_with_business = Contact.objects.create(
            name="John Vendor",
            business=self.business1
        )

        # Create contact without business
        self.contact_without_business = Contact.objects.create(
            name="Jane Independent"
        )

    def test_bill_auto_associates_business_from_contact_on_creation(self):
        """
        Test that when creating a Bill with a Contact that has a Business,
        the Business is automatically associated with the Bill.
        """
        bill = Bill.objects.create(
            bill_number="BILL-039",
            contact=self.contact_with_business,
            vendor_invoice_number="INV001"
        )

        # Verify business was auto-associated from contact
        self.assertEqual(bill.business, self.business1)
        self.assertEqual(bill.business, self.contact_with_business.business)

    def test_bill_no_business_when_contact_has_no_business(self):
        """
        Test that when creating a Bill with a Contact that has no Business,
        the Bill's business field remains None.
        """
        bill = Bill.objects.create(
            bill_number="BILL-040",
            contact=self.contact_without_business,
            vendor_invoice_number="INV002"
        )

        # Verify no business is associated
        self.assertIsNone(bill.business)

    def test_bill_explicit_business_not_overridden(self):
        """
        Test that when creating a Bill with an explicitly set Business,
        that Business is used and not overridden by the Contact's business.
        """
        bill = Bill.objects.create(
            bill_number="BILL-041",
            contact=self.contact_with_business,
            business=self.business2,  # Explicitly set different business
            vendor_invoice_number="INV003"
        )

        # Verify the explicitly set business is used
        self.assertEqual(bill.business, self.business2)
        self.assertNotEqual(bill.business, self.contact_with_business.business)

    def test_bill_business_not_changed_on_update(self):
        """
        Test that when updating an existing Bill, the business is not changed.
        """
        # Create bill with auto-associated business
        bill = Bill.objects.create(
            bill_number="BILL-042",
            contact=self.contact_with_business,
            vendor_invoice_number="INV004"
        )

        # Verify initial business
        self.assertEqual(bill.business, self.business1)

        # Update the contact's business
        self.contact_with_business.business = self.business2
        self.contact_with_business.save()

        # Update the bill (change vendor invoice number)
        bill.vendor_invoice_number = "INV004-UPDATED"
        bill.save()

        # Verify business was NOT updated
        self.assertEqual(bill.business, self.business1)
        self.assertNotEqual(bill.business, self.contact_with_business.business)

    def test_bill_business_remains_none_on_update_if_initially_none(self):
        """
        Test that if a Bill was created without a business (contact had no business),
        it remains None on updates even if the contact later gets a business.
        """
        # Create bill with contact that has no business
        bill = Bill.objects.create(
            bill_number="BILL-043",
            contact=self.contact_without_business,
            vendor_invoice_number="INV005"
        )

        # Verify no business initially
        self.assertIsNone(bill.business)

        # Update the contact to have a business
        self.contact_without_business.business = self.business1
        self.contact_without_business.save()

        # Update the bill
        bill.vendor_invoice_number = "INV005-UPDATED"
        bill.save()

        # Verify business is still None (not auto-updated)
        self.assertIsNone(bill.business)

    def test_bill_with_purchase_order_auto_associates_business(self):
        """
        Test that Bill auto-associates business even when created with a PurchaseOrder.
        """
        # Create a purchase order in issued status
        po = PurchaseOrder.objects.create(
            business=self.business1,
            po_number="PO001",
            status='draft'
        )
        po.status = 'issued'
        po.save()

        # Create bill with PO and contact with business
        bill = Bill.objects.create(
            bill_number="BILL-044",
            purchase_order=po,
            contact=self.contact_with_business,
            vendor_invoice_number="INV006"
        )

        # Verify business was auto-associated
        self.assertEqual(bill.business, self.business1)
