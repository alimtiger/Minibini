from django.test import TestCase
from apps.purchasing.models import PurchaseOrder, Bill
from apps.jobs.models import Job
from apps.contacts.models import Contact
from .base import FixtureTestCase


class PurchaseOrderModelFixtureTest(FixtureTestCase):
    """
    Test PurchaseOrder model using fixture data loaded from unit_test_data.json
    """
    
    def test_purchase_orders_exist_from_fixture(self):
        """Test that purchase orders from fixture data exist and have correct properties"""
        po1 = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        self.assertEqual(po1.price_list_item_id, "PLI001")
        self.assertEqual(po1.job_id.job_number, "JOB-2024-0001")
        
        po2 = PurchaseOrder.objects.get(po_number="PO-2024-0002")
        self.assertEqual(po2.price_list_item_id, "PLI002")
        self.assertEqual(po2.job_id.job_number, "JOB-2024-0002")
        
    def test_purchase_order_str_method_with_fixture_data(self):
        """Test purchase order string representation with fixture data"""
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        self.assertEqual(str(po), "PO PO-2024-0001")
        
    def test_purchase_order_job_relationships(self):
        """Test that purchase orders are properly linked to jobs"""
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(po.job_id, job)
        
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
            job_id=job,
            price_list_item_id="PLI003",
            po_number="PO-2024-0003"
        )
        self.assertEqual(new_po.job_id, job)
        self.assertEqual(PurchaseOrder.objects.count(), 3)  # 2 from fixture + 1 new
        
    def test_purchase_order_without_job(self):
        """Test creating purchase order without job relationship"""
        po_without_job = PurchaseOrder.objects.create(
            price_list_item_id="PLI004",
            po_number="PO-2024-0004"
        )
        self.assertIsNone(po_without_job.job_id)
        self.assertEqual(po_without_job.price_list_item_id, "PLI004")
        
    def test_purchase_order_cascade_behavior(self):
        """Test purchase order behavior when related job is deleted"""
        # Create a new job for this test
        contact = Contact.objects.get(name="John Doe")
        test_job = Job.objects.create(
            job_number="JOB-TEST-DELETE",
            contact_id=contact,
            description="Test job for deletion"
        )
        
        # Create PO linked to this job
        test_po = PurchaseOrder.objects.create(
            job_id=test_job,
            price_list_item_id="PLI999",
            po_number="PO-TEST-DELETE"
        )
        po_id = test_po.po_id
        
        # Delete the job - PO should also be deleted due to CASCADE
        test_job.delete()
        
        # PO should be deleted due to CASCADE
        with self.assertRaises(PurchaseOrder.DoesNotExist):
            PurchaseOrder.objects.get(po_id=po_id)


class BillModelFixtureTest(FixtureTestCase):
    """
    Test Bill model using fixture data
    """
    
    def test_bills_exist_from_fixture(self):
        """Test that bills from fixture data exist and have correct properties"""
        bill1 = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        self.assertEqual(bill1.po_id.po_number, "PO-2024-0001")
        self.assertEqual(bill1.contact_id.name, "Acme Vendor")
        
        bill2 = Bill.objects.get(vendor_invoice_number="ACME-INV-002")
        self.assertEqual(bill2.po_id.po_number, "PO-2024-0002")
        self.assertEqual(bill2.contact_id.name, "Acme Vendor")
        
    def test_bill_str_method_with_fixture_data(self):
        """Test bill string representation with fixture data"""
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        expected_str = f"Bill {bill.bill_id}"
        self.assertEqual(str(bill), expected_str)
        
    def test_bill_purchase_order_relationships(self):
        """Test that bills are properly linked to purchase orders"""
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        self.assertEqual(bill.po_id, po)
        
    def test_bill_contact_relationships(self):
        """Test that bills are properly linked to vendor contacts"""
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        vendor = Contact.objects.get(name="Acme Vendor")
        self.assertEqual(bill.contact_id, vendor)
        
    def test_create_new_bill_with_existing_relationships(self):
        """Test creating a new bill with existing PO and contact from fixtures"""
        po = PurchaseOrder.objects.get(po_number="PO-2024-0001")
        vendor = Contact.objects.get(name="Acme Vendor")
        
        new_bill = Bill.objects.create(
            po_id=po,
            contact_id=vendor,
            vendor_invoice_number="ACME-INV-003"
        )
        
        self.assertEqual(new_bill.po_id, po)
        self.assertEqual(new_bill.contact_id, vendor)
        self.assertEqual(Bill.objects.count(), 3)  # 2 from fixture + 1 new
        
    def test_bill_cascade_delete_with_purchase_order(self):
        """Test that bill is deleted when purchase order is deleted (CASCADE)"""
        # Get existing bill and its PO
        bill = Bill.objects.get(vendor_invoice_number="ACME-INV-001")
        po = bill.po_id
        bill_id = bill.bill_id
        
        # Delete the purchase order
        po.delete()
        
        # Bill should be deleted due to CASCADE
        with self.assertRaises(Bill.DoesNotExist):
            Bill.objects.get(bill_id=bill_id)
            
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
            po_id=po,
            contact_id=test_vendor,
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
        job_through_po = bill.po_id.job_id
        expected_job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(job_through_po, expected_job)
        
        # Verify we can get the customer contact through this relationship
        customer_contact = job_through_po.contact_id
        expected_customer = Contact.objects.get(name="John Doe")
        self.assertEqual(customer_contact, expected_customer)