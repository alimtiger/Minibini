from django.test import TestCase
from decimal import Decimal
from apps.invoicing.models import Invoice, LineItem, PriceListItem, ItemType
from apps.jobs.models import Job, Estimate, Task
from .base import FixtureTestCase


class ItemTypeModelFixtureTest(FixtureTestCase):
    """
    Test ItemType model using fixture data loaded from unit_test_data.json
    """
    
    def test_item_types_exist_from_fixture(self):
        """Test that item types from fixture data exist and have correct properties"""
        hardware = ItemType.objects.get(name="Hardware")
        self.assertEqual(hardware.taxability, "taxable")
        self.assertEqual(hardware.mapping_to_task, "installation")
        
        labor = ItemType.objects.get(name="Labor")
        self.assertEqual(labor.taxability, "taxable")
        self.assertEqual(labor.mapping_to_task, "labor")
        
        materials = ItemType.objects.get(name="Materials")
        self.assertEqual(materials.taxability, "non_taxable")
        self.assertEqual(materials.mapping_to_task, "supply")
        
    def test_item_type_str_method_with_fixture_data(self):
        """Test item type string representation with fixture data"""
        item_type = ItemType.objects.get(name="Hardware")
        self.assertEqual(str(item_type), "Hardware")
        
    def test_create_new_item_type(self):
        """Test creating a new item type alongside existing fixture data"""
        new_type = ItemType.objects.create(
            name="Software",
            taxability="exempt",
            mapping_to_task="configuration"
        )
        self.assertEqual(new_type.name, "Software")
        self.assertEqual(ItemType.objects.count(), 4)  # 3 from fixture + 1 new


class PriceListItemModelFixtureTest(FixtureTestCase):
    """
    Test PriceListItem model using fixture data
    """
    
    def test_price_list_items_exist_from_fixture(self):
        """Test that price list items from fixture data exist and have correct properties"""
        screw_item = PriceListItem.objects.get(code="SCREW001")
        self.assertEqual(screw_item.description, "Stainless steel screws 2.5 inch")
        self.assertEqual(screw_item.purchase_price, Decimal('0.25'))
        self.assertEqual(screw_item.selling_price, Decimal('0.50'))
        self.assertEqual(screw_item.qty_on_hand, Decimal('1000.00'))
        self.assertEqual(screw_item.qty_sold, Decimal('150.00'))
        self.assertEqual(screw_item.qty_wasted, Decimal('5.00'))
        self.assertEqual(screw_item.item_type_id.name, "Hardware")
        
        labor_item = PriceListItem.objects.get(code="LABOR001")
        self.assertEqual(labor_item.description, "Skilled labor hourly rate")
        self.assertEqual(labor_item.purchase_price, Decimal('0.00'))
        self.assertEqual(labor_item.selling_price, Decimal('75.00'))
        self.assertEqual(labor_item.qty_on_hand, Decimal('0.00'))
        self.assertEqual(labor_item.qty_sold, Decimal('240.00'))
        self.assertEqual(labor_item.item_type_id.name, "Labor")
        
    def test_price_list_item_str_method_with_fixture_data(self):
        """Test price list item string representation with fixture data"""
        item = PriceListItem.objects.get(code="SCREW001")
        expected_str = "SCREW001 - Stainless steel screws 2.5 inch"
        self.assertEqual(str(item), expected_str)
        
    def test_price_list_item_type_relationships(self):
        """Test that price list items are properly linked to item types"""
        screw_item = PriceListItem.objects.get(code="SCREW001")
        hardware_type = ItemType.objects.get(name="Hardware")
        self.assertEqual(screw_item.item_type_id, hardware_type)
        
    def test_create_new_price_list_item(self):
        """Test creating a new price list item with existing item type from fixtures"""
        materials_type = ItemType.objects.get(name="Materials")
        new_item = PriceListItem.objects.create(
            item_type_id=materials_type,
            code="WOOD001",
            unit_parts_labor="board_foot",
            description="Oak lumber 1x6",
            purchase_price=Decimal('3.50'),
            selling_price=Decimal('5.25')
        )
        self.assertEqual(new_item.code, "WOOD001")
        self.assertEqual(PriceListItem.objects.count(), 3)  # 2 from fixture + 1 new


class InvoiceModelFixtureTest(FixtureTestCase):
    """
    Test Invoice model using fixture data
    """
    
    def test_invoices_exist_from_fixture(self):
        """Test that invoices from fixture data exist and have correct properties"""
        invoice1 = Invoice.objects.get(invoice_number="INV-2024-0001")
        self.assertEqual(invoice1.status, "active")
        self.assertEqual(invoice1.job_id.job_number, "JOB-2024-0001")
        
        invoice2 = Invoice.objects.get(invoice_number="INV-2024-0002")
        self.assertEqual(invoice2.status, "active")
        self.assertEqual(invoice2.job_id.job_number, "JOB-2024-0002")
        
    def test_invoice_str_method_with_fixture_data(self):
        """Test invoice string representation with fixture data"""
        invoice = Invoice.objects.get(invoice_number="INV-2024-0001")
        self.assertEqual(str(invoice), "Invoice INV-2024-0001")
        
    def test_invoice_job_relationships(self):
        """Test that invoices are properly linked to jobs"""
        invoice = Invoice.objects.get(invoice_number="INV-2024-0001")
        job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(invoice.job_id, job)
        
    def test_invoice_status_update(self):
        """Test updating invoice status using fixture data"""
        invoice = Invoice.objects.get(invoice_number="INV-2024-0001")
        self.assertEqual(invoice.status, "active")
        
        invoice.status = "cancelled"
        invoice.save()
        
        updated_invoice = Invoice.objects.get(invoice_number="INV-2024-0001")
        self.assertEqual(updated_invoice.status, "cancelled")
        
    def test_create_new_invoice_for_existing_job(self):
        """Test creating a new invoice for existing job from fixtures"""
        job = Job.objects.get(job_number="JOB-2024-0001")
        new_invoice = Invoice.objects.create(
            job_id=job,
            invoice_number="INV-2024-0003",
            status="active"
        )
        self.assertEqual(new_invoice.job_id, job)
        self.assertEqual(Invoice.objects.count(), 3)  # 2 from fixture + 1 new


class LineItemModelFixtureTest(FixtureTestCase):
    """
    Test LineItem model using fixture data
    """
    
    def test_line_items_exist_from_fixture(self):
        """Test that line items from fixture data exist and have correct properties"""
        line_item1 = LineItem.objects.get(central_line_item_number="CLI001")
        self.assertEqual(line_item1.qty, Decimal('50.00'))
        self.assertEqual(line_item1.unit_parts_labor, "each")
        self.assertEqual(line_item1.description, "Screws for kitchen cabinet installation")
        self.assertEqual(line_item1.price_currency, Decimal('25.00'))
        self.assertEqual(line_item1.estimate_id.estimate_number, "EST-2024-0001")
        self.assertEqual(line_item1.invoice_id.invoice_number, "INV-2024-0001")
        self.assertEqual(line_item1.task_id.name, "Kitchen demolition")
        self.assertEqual(line_item1.price_list_item_id.code, "SCREW001")
        
        line_item2 = LineItem.objects.get(central_line_item_number="CLI002")
        self.assertEqual(line_item2.qty, Decimal('8.00'))
        self.assertEqual(line_item2.unit_parts_labor, "hour")
        self.assertEqual(line_item2.description, "Electrical rough-in labor")
        self.assertEqual(line_item2.price_currency, Decimal('600.00'))
        self.assertEqual(line_item2.task_id.name, "Electrical rough-in")
        self.assertEqual(line_item2.price_list_item_id.code, "LABOR001")
        
    def test_line_item_str_method_with_fixture_data(self):
        """Test line item string representation with fixture data"""
        line_item = LineItem.objects.get(central_line_item_number="CLI001")
        expected_str = f"Line Item {line_item.line_item_id}"
        self.assertEqual(str(line_item), expected_str)
        
    def test_line_item_relationships(self):
        """Test that line items are properly linked to related models"""
        line_item = LineItem.objects.get(central_line_item_number="CLI001")
        
        # Test estimate relationship
        estimate = Estimate.objects.get(estimate_number="EST-2024-0001")
        self.assertEqual(line_item.estimate_id, estimate)
        
        # Test invoice relationship
        invoice = Invoice.objects.get(invoice_number="INV-2024-0001")
        self.assertEqual(line_item.invoice_id, invoice)
        
        # Test task relationship
        task = Task.objects.get(name="Kitchen demolition")
        self.assertEqual(line_item.task_id, task)
        
        # Test price list item relationship
        price_item = PriceListItem.objects.get(code="SCREW001")
        self.assertEqual(line_item.price_list_item_id, price_item)
        
    def test_line_item_calculations(self):
        """Test line item calculations using fixture data"""
        line_item1 = LineItem.objects.get(central_line_item_number="CLI001")
        # 50 screws at $0.50 each = $25.00 total
        expected_total = line_item1.qty * line_item1.price_list_item_id.selling_price
        self.assertEqual(line_item1.price_currency, expected_total)
        
        line_item2 = LineItem.objects.get(central_line_item_number="CLI002")
        # 8 hours at $75.00 per hour = $600.00 total
        expected_total = line_item2.qty * line_item2.price_list_item_id.selling_price
        self.assertEqual(line_item2.price_currency, expected_total)
        
    def test_create_new_line_item_with_existing_relationships(self):
        """Test creating a new line item with existing related objects from fixtures"""
        estimate = Estimate.objects.get(estimate_number="EST-2024-0001")
        invoice = Invoice.objects.get(invoice_number="INV-2024-0001")
        task = Task.objects.get(name="Kitchen demolition")
        price_item = PriceListItem.objects.get(code="LABOR001")
        
        new_line_item = LineItem.objects.create(
            estimate_id=estimate,
            invoice_id=invoice,
            task_id=task,
            price_list_item_id=price_item,
            central_line_item_number="CLI003",
            qty=Decimal('2.00'),
            unit_parts_labor="hour",
            description="Cleanup labor",
            price_currency=Decimal('150.00')
        )
        
        self.assertEqual(new_line_item.estimate_id, estimate)
        self.assertEqual(new_line_item.task_id, task)
        self.assertEqual(LineItem.objects.count(), 3)  # 2 from fixture + 1 new