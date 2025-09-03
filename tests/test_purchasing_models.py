from django.test import TestCase
from apps.purchasing.models import PurchaseOrder, Bill
from apps.jobs.models import Job
from apps.contacts.models import Contact


class PurchaseOrderModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact,
            description="Test job"
        )
        
    def test_purchase_order_creation(self):
        po = PurchaseOrder.objects.create(
            job=self.job,
            price_list_item=None,
            po_number="PO001"
        )
        self.assertEqual(po.job, self.job)
        self.assertIsNone(po.price_list_item)
        self.assertEqual(po.po_number, "PO001")
        
    def test_purchase_order_str_method(self):
        po = PurchaseOrder.objects.create(po_number="PO002")
        self.assertEqual(str(po), "PO PO002")
        
    def test_purchase_order_optional_job(self):
        po = PurchaseOrder.objects.create(
            po_number="PO003",
            price_list_item=None
        )
        self.assertIsNone(po.job)
        self.assertIsNone(po.price_list_item)
        
    def test_purchase_order_optional_price_list_item(self):
        po = PurchaseOrder.objects.create(
            job=self.job,
            po_number="PO004"
        )
        self.assertEqual(po.job, self.job)
        self.assertIsNone(po.price_list_item)
        
    def test_purchase_order_unique_po_number(self):
        PurchaseOrder.objects.create(po_number="UNIQUE001")
        
        with self.assertRaises(Exception):
            PurchaseOrder.objects.create(po_number="UNIQUE001")


class BillModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Vendor")
        self.customer_contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.customer_contact,
            description="Test job"
        )
        self.purchase_order = PurchaseOrder.objects.create(
            job=self.job,
            po_number="PO001"
        )
        
    def test_bill_creation(self):
        bill = Bill.objects.create(
            purchase_order=self.purchase_order,
            contact=self.contact,
            vendor_invoice_number="VIN001"
        )
        self.assertEqual(bill.purchase_order, self.purchase_order)
        self.assertEqual(bill.contact, self.contact)
        self.assertEqual(bill.vendor_invoice_number, "VIN001")
        
    def test_bill_str_method(self):
        bill = Bill.objects.create(
            purchase_order=self.purchase_order,
            contact=self.contact,
            vendor_invoice_number="VIN002"
        )
        self.assertEqual(str(bill), f"Bill {bill.bill_id}")
        
    def test_bill_cascade_delete_with_po(self):
        bill = Bill.objects.create(
            purchase_order=self.purchase_order,
            contact=self.contact,
            vendor_invoice_number="VIN003"
        )
        bill_id = bill.bill_id
        
        # Delete the purchase order
        self.purchase_order.delete()
        
        # Bill should be deleted due to CASCADE
        with self.assertRaises(Bill.DoesNotExist):
            Bill.objects.get(bill_id=bill_id)
            
    def test_bill_with_contact_deletion(self):
        bill = Bill.objects.create(
            purchase_order=self.purchase_order,
            contact=self.contact,
            vendor_invoice_number="VIN004"
        )
        contact_id = self.contact.contact_id
        
        # Delete the contact
        self.contact.delete()
        
        # Bill should be deleted due to CASCADE
        with self.assertRaises(Bill.DoesNotExist):
            Bill.objects.get(purchase_order=self.purchase_order, vendor_invoice_number="VIN004")