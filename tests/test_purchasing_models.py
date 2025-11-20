from django.test import TestCase
from django.db import models
from apps.purchasing.models import PurchaseOrder, Bill
from apps.jobs.models import Job
from apps.contacts.models import Contact, Business


class PurchaseOrderModelTest(TestCase):
    def setUp(self):
        self.business = Business.objects.create(business_name="Test Business")
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact,
            description="Test job"
        )
        
    def test_purchase_order_creation(self):
        po = PurchaseOrder.objects.create(
            business=self.business,
            job=self.job,
            po_number="PO001"
        )
        self.assertEqual(po.job, self.job)
        self.assertEqual(po.po_number, "PO001")
        
    def test_purchase_order_str_method(self):
        po = PurchaseOrder.objects.create(business=self.business, po_number="PO002")
        self.assertEqual(str(po), "PO PO002")
        
    def test_purchase_order_optional_job(self):
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number="PO003"
        )
        self.assertIsNone(po.job)

    def test_purchase_order_without_job(self):
        po = PurchaseOrder.objects.create(
            business=self.business,
            po_number="PO004"
        )
        self.assertIsNone(po.job)
        self.assertEqual(po.po_number, "PO004")
        
    def test_purchase_order_unique_po_number(self):
        PurchaseOrder.objects.create(business=self.business, po_number="UNIQUE001")
        
        with self.assertRaises(Exception):
            PurchaseOrder.objects.create(business=self.business, po_number="UNIQUE001")


class BillModelTest(TestCase):
    def setUp(self):
        self.business = Business.objects.create(business_name="Test Business")
        self.contact = Contact.objects.create(
            name="Test Vendor",
            business=self.business
        )
        self.customer_contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.customer_contact,
            description="Test job"
        )
        self.purchase_order = PurchaseOrder.objects.create(
            business=self.business,
            job=self.job,
            po_number="PO001",
            status='draft'
        )
        self.purchase_order.status = 'issued'
        self.purchase_order.save()
        
    def test_bill_creation(self):
        bill = Bill.objects.create(
            bill_number="BILL-001",
            purchase_order=self.purchase_order,
            business=self.business,
            contact=self.contact,
            vendor_invoice_number="VIN001"
        )
        self.assertEqual(bill.purchase_order, self.purchase_order)
        self.assertEqual(bill.business, self.business)
        self.assertEqual(bill.contact, self.contact)
        self.assertEqual(bill.vendor_invoice_number, "VIN001")
        
    def test_bill_str_method(self):
        bill = Bill.objects.create(
            bill_number="BILL-002",
            purchase_order=self.purchase_order,
            business=self.business,
            contact=self.contact,
            vendor_invoice_number="VIN002"
        )
        self.assertEqual(str(bill), f"Bill {bill.bill_number}")
        
    def test_bill_set_null_on_po_delete(self):
        bill = Bill.objects.create(
            bill_number="BILL-003",
            purchase_order=self.purchase_order,
            business=self.business,
            contact=self.contact,
            vendor_invoice_number="VIN003"
        )
        bill_id = bill.bill_id

        # Delete the purchase order
        self.purchase_order.delete()

        # Bill should still exist but with purchase_order set to None due to SET_NULL
        bill.refresh_from_db()
        self.assertIsNone(bill.purchase_order)
            
    def test_bill_with_contact_deletion(self):
        bill = Bill.objects.create(
            bill_number="BILL-004",
            purchase_order=self.purchase_order,
            business=self.business,
            contact=self.contact,
            vendor_invoice_number="VIN004"
        )
        contact_id = self.contact.pk

        # Cannot delete the contact due to PROTECT
        with self.assertRaises(models.ProtectedError):
            self.contact.delete()
