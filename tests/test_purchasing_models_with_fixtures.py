from django.test import TestCase
from apps.purchasing.models import PurchaseOrder, Bill
from apps.jobs.models import Job
from apps.contacts.models import Contact


class PurchaseOrderModelFixtureTest(TestCase):
    """
    Test PurchaseOrder model using fixture data
    """
    fixtures = ['core_base_data.json', 'contacts_base_data.json', 'jobs_basic_data.json', 'invoicing_data.json', 'purchasing_data.json']

    def test_purchase_orders_exist_from_fixture(self):
        """Test that purchase orders from fixture data exist and have correct properties"""
        po1 = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        self.assertEqual(po1.job.job_number, "JOB-2024-0001")

        po2 = PurchaseOrder.objects.get(po_number="PO-2024-0002")
        self.assertEqual(po2.job.job_number, "JOB-2024-0002")

    def test_purchase_order_str_method_with_fixture_data(self):
        """Test purchase order string representation with fixture data"""
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        self.assertEqual(str(po), "PO PO-2024-0001")

    def test_purchase_order_job_relationships(self):
        """Test that purchase orders are properly linked to jobs"""
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(po.job, job)

    def test_purchase_order_unique_po_number(self):
        """Test that PO numbers are unique using fixture data as baseline"""
        # Verify existing PO numbers from fixture
        self.assertTrue(PurchaseOrder.objects.filter(po_number="PO-2024-0001").exists())

        # Try to create duplicate - should fail
        with self.assertRaises(Exception):
            PurchaseOrder.objects.create(po_number="PO-2024-0001")

    def test_create_new_purchase_order_with_existing_job(self):
        """Test creating a new purchase order for existing job from fixtures"""
        job = Job.objects.get(job_number="JOB-2024-0001")
        new_po = PurchaseOrder.objects.create(
            job=job,
#            price_list_item=po1.price_list_item,
            po_number="PO-2024-0003"
        )
        self.assertEqual(new_po.job, job)
        self.assertEqual(PurchaseOrder.objects.count(), 3)  # 2 from fixture + 1 new

    def test_purchase_order_without_job(self):
        """Test creating purchase order without job relationship"""
        po_without_job = PurchaseOrder.objects.create(
            po_number="PO-2024-0004"
        )
        self.assertIsNone(po_without_job.job)

    def test_purchase_order_cascade_behavior(self):
        """Test purchase order behavior when related job is deleted"""
        # Create a new job for this test
        contact = Contact.objects.get(name="John Doe")
        test_job = Job.objects.create(
            job_number="JOB-TEST-DELETE",
            contact=contact,
            description="Test job for deletion"
        )

        # Create PO linked to this job
        test_po = PurchaseOrder.objects.create(
            job=test_job,
            po_number="PO-TEST-DELETE"
        )
        po_id = test_po.po_id

        # Delete the job - PO should also be deleted due to CASCADE
        test_job.delete()

        # PO should be deleted due to CASCADE
        with self.assertRaises(PurchaseOrder.DoesNotExist):
            PurchaseOrder.objects.get(po_id=po_id)


class BillModelFixtureTest(TestCase):
    """
    Test Bill model using fixture data
    """
    fixtures = ['core_base_data.json', 'contacts_base_data.json', 'jobs_basic_data.json', 'invoicing_data.json', 'purchasing_data.json']

    def test_bills_exist_from_fixture(self):
        """Test that bills from fixture data exist and have correct properties"""
        bill1 = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        self.assertEqual(bill1.purchase_order.po_number, "PO-2024-0001")
        self.assertEqual(bill1.contact.name, "Acme Vendor")

        bill2 = Bill.objects.get(vendor_invoice_number="ACME-INV-002")
        self.assertEqual(bill2.purchase_order.po_number, "PO-2024-0002")
        self.assertEqual(bill2.contact.name, "Acme Vendor")

    def test_bill_str_method_with_fixture_data(self):
        """Test bill string representation with fixture data"""
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        expected_str = f"Bill {bill.bill_number}"
        self.assertEqual(str(bill), expected_str)

    def test_bill_purchase_order_relationships(self):
        """Test that bills are properly linked to purchase orders"""
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        self.assertEqual(bill.purchase_order, po)

    def test_bill_contact_relationships(self):
        """Test that bills are properly linked to vendor contacts"""
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        vendor = Contact.objects.get(name="Acme Vendor")
        self.assertEqual(bill.contact, vendor)

    def test_create_new_bill_with_existing_relationships(self):
        """Test creating a new bill with existing PO and contact from fixtures"""
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        vendor = Contact.objects.get(name="Acme Vendor")

        new_bill = Bill.objects.create(
            purchase_order=po,
            contact=vendor,
            bill_number='BILL-TEST',
            vendor_invoice_number="ACME-INV-003"
        )

        self.assertEqual(new_bill.purchase_order, po)
        self.assertEqual(new_bill.contact, vendor)
        self.assertEqual(Bill.objects.count(), 3)  # 2 from fixture + 1 new

    def test_bill_set_null_on_purchase_order_delete(self):
        """Test that bill purchase_order is set to None when purchase order is deleted (SET_NULL)"""
        # Get existing bill and its PO
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        po = bill.purchase_order
        bill_id = bill.bill_id

        # Delete the purchase order
        po.delete()

        # Bill should still exist but with purchase_order set to None due to SET_NULL
        bill.refresh_from_db()
        self.assertIsNone(bill.purchase_order)

    def test_bill_cascade_delete_with_contact(self):
        """Test that bill is deleted when vendor contact is deleted (CASCADE)"""
        # Create a new vendor contact for this test to avoid affecting other tests
        test_vendor = Contact.objects.create(
            name="Test Vendor",
            email="test@vendor.com"
        )

        # Create a new PO and bill for this test
        po = PurchaseOrder.objects.get(po_number="PO-2024-0002")
        test_bill = Bill.objects.create(
            purchase_order=po,
            contact=test_vendor,
            bill_number='BILL-TEST',
            vendor_invoice_number="TEST-INV-001"
        )
        bill_id = test_bill.bill_id

        # Delete the vendor contact
        test_vendor.delete()

        # Bill should be deleted due to CASCADE
        with self.assertRaises(Bill.DoesNotExist):
            Bill.objects.get(bill_id=bill_id)

    def test_bill_relationships_through_job(self):
        """Test bill relationships that trace back to jobs through purchase orders"""
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")

        # Trace relationship: Bill -> PO -> Job
        job_through_po = bill.purchase_order.job
        expected_job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(job_through_po, expected_job)

        # Verify we can get the customer contact through this relationship
        customer_contact = job_through_po.contact
        expected_customer = Contact.objects.get(name="John Doe")
        self.assertEqual(customer_contact, expected_customer)
