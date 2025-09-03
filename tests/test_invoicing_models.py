from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.invoicing.models import Invoice, LineItem, PriceListItem, ItemType
from apps.jobs.models import Job, Estimate, Task, WorkOrder
from apps.purchasing.models import PurchaseOrder, Bill
from apps.contacts.models import Contact


class ItemTypeModelTest(TestCase):
    def test_item_type_creation(self):
        item_type = ItemType.objects.create(
            name="Hardware",
            taxability="taxable",
            mapping_to_task="installation"
        )
        self.assertEqual(item_type.name, "Hardware")
        self.assertEqual(item_type.taxability, "taxable")
        self.assertEqual(item_type.mapping_to_task, "installation")
        
    def test_item_type_str_method(self):
        item_type = ItemType.objects.create(name="Software")
        self.assertEqual(str(item_type), "Software")
        
    def test_item_type_optional_fields(self):
        item_type = ItemType.objects.create(name="Basic Type")
        self.assertEqual(item_type.taxability, "")
        self.assertEqual(item_type.mapping_to_task, "")


class PriceListItemModelTest(TestCase):
    def setUp(self):
        self.item_type = ItemType.objects.create(name="Test Type")
        
    def test_price_list_item_creation(self):
        item = PriceListItem.objects.create(
            item_type_id=self.item_type,
            code="ITEM001",
            unit_parts_labor="each",
            description="Test item description",
            purchase_price=Decimal('10.50'),
            selling_price=Decimal('15.75'),
            qty_on_hand=Decimal('100.00'),
            qty_sold=Decimal('25.00'),
            qty_wasted=Decimal('2.00')
        )
        self.assertEqual(item.item_type_id, self.item_type)
        self.assertEqual(item.code, "ITEM001")
        self.assertEqual(item.unit_parts_labor, "each")
        self.assertEqual(item.description, "Test item description")
        self.assertEqual(item.purchase_price, Decimal('10.50'))
        self.assertEqual(item.selling_price, Decimal('15.75'))
        self.assertEqual(item.qty_on_hand, Decimal('100.00'))
        self.assertEqual(item.qty_sold, Decimal('25.00'))
        self.assertEqual(item.qty_wasted, Decimal('2.00'))
        
    def test_price_list_item_str_method(self):
        item = PriceListItem.objects.create(
            item_type_id=self.item_type,
            code="TEST123",
            description="This is a very long description that should be truncated in the string representation"
        )
        self.assertEqual(str(item), "TEST123 - This is a very long description that should be tru")
        
    def test_price_list_item_defaults(self):
        item = PriceListItem.objects.create(
            item_type_id=self.item_type,
            code="DEFAULT001"
        )
        self.assertEqual(item.purchase_price, Decimal('0.00'))
        self.assertEqual(item.selling_price, Decimal('0.00'))
        self.assertEqual(item.qty_on_hand, Decimal('0.00'))
        self.assertEqual(item.qty_sold, Decimal('0.00'))
        self.assertEqual(item.qty_wasted, Decimal('0.00'))


class InvoiceModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact,
            description="Test job"
        )
        
    def test_invoice_creation(self):
        invoice = Invoice.objects.create(
            job_id=self.job,
            invoice_number="INV001",
            status='active'
        )
        self.assertEqual(invoice.job_id, self.job)
        self.assertEqual(invoice.invoice_number, "INV001")
        self.assertEqual(invoice.status, 'active')
        
    def test_invoice_str_method(self):
        invoice = Invoice.objects.create(
            job_id=self.job,
            invoice_number="INV002"
        )
        self.assertEqual(str(invoice), "Invoice INV002")
        
    def test_invoice_default_status(self):
        invoice = Invoice.objects.create(
            job_id=self.job,
            invoice_number="INV003"
        )
        self.assertEqual(invoice.status, 'active')
        
    def test_invoice_status_choices(self):
        invoice = Invoice.objects.create(
            job_id=self.job,
            invoice_number="INV004",
            status='cancelled'
        )
        self.assertEqual(invoice.status, 'cancelled')


class LineItemModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact,
            description="Test job"
        )
        self.invoice = Invoice.objects.create(
            job_id=self.job,
            invoice_number="INV001"
        )
        self.estimate = Estimate.objects.create(
            job_id=self.job,
            estimate_number="EST001"
        )
        self.work_order = WorkOrder.objects.create(job_id=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
            task_type="standard"
        )
        self.purchase_order = PurchaseOrder.objects.create(
            job_id=self.job,
            po_number="PO001"
        )
        self.bill = Bill.objects.create(
            po_id=self.purchase_order,
            contact_id=self.contact,
            vendor_invoice_number="VIN001"
        )
        self.item_type = ItemType.objects.create(name="Test Type")
        self.price_list_item = PriceListItem.objects.create(
            item_type_id=self.item_type,
            code="ITEM001"
        )
        
    def test_line_item_creation(self):
        line_item = LineItem.objects.create(
            estimate_id=self.estimate,
            po_id=self.purchase_order,
            bill_id=self.bill,
            invoice_id=self.invoice,
            task_id=self.task,
            price_list_item_id=self.price_list_item,
            central_line_item_number="CLI001",
            qty=Decimal('5.00'),
            unit_parts_labor="hours",
            description="Test line item",
            price_currency=Decimal('50.00')
        )
        self.assertEqual(line_item.estimate_id, self.estimate)
        self.assertEqual(line_item.po_id, self.purchase_order)
        self.assertEqual(line_item.bill_id, self.bill)
        self.assertEqual(line_item.invoice_id, self.invoice)
        self.assertEqual(line_item.task_id, self.task)
        self.assertEqual(line_item.price_list_item_id, self.price_list_item)
        self.assertEqual(line_item.central_line_item_number, "CLI001")
        self.assertEqual(line_item.qty, Decimal('5.00'))
        self.assertEqual(line_item.unit_parts_labor, "hours")
        self.assertEqual(line_item.description, "Test line item")
        self.assertEqual(line_item.price_currency, Decimal('50.00'))
        
    def test_line_item_str_method(self):
        line_item = LineItem.objects.create()
        self.assertEqual(str(line_item), f"Line Item {line_item.line_item_id}")
        
    def test_line_item_defaults(self):
        line_item = LineItem.objects.create()
        self.assertEqual(line_item.qty, Decimal('0.00'))
        self.assertEqual(line_item.price_currency, Decimal('0.00'))
        
    def test_line_item_optional_relationships(self):
        line_item = LineItem.objects.create(
            qty=Decimal('1.00'),
            description="Simple line item"
        )
        self.assertIsNone(line_item.estimate_id)
        self.assertIsNone(line_item.po_id)
        self.assertIsNone(line_item.bill_id)
        self.assertIsNone(line_item.invoice_id)
        self.assertIsNone(line_item.task_id)
        self.assertIsNone(line_item.price_list_item_id)