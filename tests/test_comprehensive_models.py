from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.contrib.auth.models import Group
from decimal import Decimal
from datetime import timedelta
from apps.contacts.models import Contact, Business, PaymentTerms
from apps.core.models import User, Configuration
from apps.jobs.models import Job, Estimate, WorkOrder, Task, Blep, TaskMapping
from apps.invoicing.models import Invoice, InvoiceLineItem, PriceListItem
from apps.jobs.models import EstimateLineItem
from apps.purchasing.models import PurchaseOrderLineItem, BillLineItem
from apps.purchasing.models import PurchaseOrder, Bill


class ComprehensiveModelIntegrationTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Manager")
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.user.groups.add(self.group)
        self.contact = Contact.objects.create(
            name="Test Contact",
            email="contact@example.com",
            addr1="123 Main St",
            city="Test City",
            municipality="TS",
            postal_code="12345"
        )
        self.payment_terms = PaymentTerms.objects.create()
        self.business = Business.objects.create(
            business_name="Test Business",
            terms=self.payment_terms
        )

    def test_complete_job_workflow(self):
        job = Job.objects.create(
            job_number="JOB001",
            status='draft',
            contact=self.contact,
            description="Test job description"
        )
        
        estimate = Estimate.objects.create(
            job=job,
            estimate_number="EST001",
            revision_number=1,
            status='open'
        )
        
        work_order = WorkOrder.objects.create(
            job=job,
            status='incomplete'
        )
        
        task = Task.objects.create(
            assignee=self.user,
            work_order=work_order,
            name="Test Task",
        )
        
        blep = Blep.objects.create(
            user=self.user,
            task=task,
            start_time=timezone.now()
        )
        
        self.assertEqual(job.status, 'draft')
        self.assertEqual(estimate.job, job)
        self.assertEqual(work_order.job, job)
        self.assertEqual(task.work_order, work_order)
        self.assertEqual(blep.task, task)

    def test_invoice_line_item_workflow(self):
        job = Job.objects.create(
            job_number="JOB002",
            contact=self.contact
        )
        
        estimate = Estimate.objects.create(
            job=job,
            estimate_number="EST002"
        )
        
        invoice = Invoice.objects.create(
            job=job,
            invoice_number="INV001"
        )
        
        price_list_item = PriceListItem.objects.create(
            code="ITEM001",
            description="Test item",
            purchase_price=Decimal('10.00'),
            selling_price=Decimal('15.00')
        )
        
        # Test creating both estimate and invoice line items
        estimate_line_item = EstimateLineItem.objects.create(
            estimate=estimate,
            price_list_item=price_list_item,
            qty=Decimal('5.00'),
            description="Test estimate line item",
            price_currency=Decimal('75.00')
        )
        
        invoice_line_item = InvoiceLineItem.objects.create(
            invoice=invoice,
            price_list_item=price_list_item,
            qty=Decimal('5.00'),
            description="Test invoice line item",
            price_currency=Decimal('75.00')
        )
        
        self.assertEqual(estimate_line_item.estimate, estimate)
        self.assertEqual(estimate_line_item.price_list_item, price_list_item)
        self.assertEqual(estimate_line_item.qty, Decimal('5.00'))
        
        self.assertEqual(invoice_line_item.invoice, invoice)
        self.assertEqual(invoice_line_item.price_list_item, price_list_item)
        self.assertEqual(invoice_line_item.qty, Decimal('5.00'))

    def test_purchase_order_workflow(self):
        job = Job.objects.create(
            job_number="JOB003",
            contact=self.contact
        )
        
        purchase_order = PurchaseOrder.objects.create(
            job=job,
            po_number="PO001"
        )
        
        bill = Bill.objects.create(
            purchase_order=purchase_order,
            contact=self.contact,
            vendor_invoice_number="VENDOR001"
        )
        
        # Test creating both purchase order and bill line items
        # Create price list item for testing
        price_item = PriceListItem.objects.create(
            code="TEST001",
            selling_price=Decimal('25.00')
        )
        
        po_line_item = PurchaseOrderLineItem.objects.create(
            purchase_order=purchase_order,
            price_list_item=price_item,
            qty=Decimal('2.00'),
            description="Purchase order item",
            price_currency=Decimal('50.00')
        )
        
        bill_line_item = BillLineItem.objects.create(
            bill=bill,
            price_list_item=price_item,
            qty=Decimal('2.00'),
            description="Bill item",
            price_currency=Decimal('50.00')
        )
        
        self.assertEqual(bill.purchase_order, purchase_order)
        self.assertEqual(po_line_item.purchase_order, purchase_order)
        self.assertEqual(bill_line_item.bill, bill)

    def test_estimate_superseding(self):
        job = Job.objects.create(
            job_number="JOB004",
            contact=self.contact
        )
        
        original_estimate = Estimate.objects.create(
            job=job,
            estimate_number="EST003",
            revision_number=1,
            status='open'
        )
        
        superseding_estimate = Estimate.objects.create(
            job=job,
            estimate_number="EST003",
            revision_number=2,
            status='open',
            superseded_by=None
        )
        
        original_estimate.superseded_by = superseding_estimate
        original_estimate.status = 'superseded'
        original_estimate.superseded_date = timezone.now()
        original_estimate.save()
        
        self.assertEqual(original_estimate.status, 'superseded')
        self.assertEqual(original_estimate.superseded_by, superseding_estimate)
        self.assertIsNotNone(original_estimate.superseded_date)

    def test_task_workflow(self):
        job = Job.objects.create(
            job_number="JOB005",
            contact=self.contact
        )
        
        work_order = WorkOrder.objects.create(job=job)
        
        task = Task.objects.create(
            work_order=work_order,
            name="Planning Task",
        )
        
        task_mapping = TaskMapping.objects.create(
            task=task,
            step_type="Planning",
            task_type_id="PLAN001",
            breakdown_of_task="Break down the planning requirements"
        )
        
        self.assertEqual(task.work_order, work_order)
        self.assertEqual(task_mapping.task, task)

    def test_configuration_number_sequences(self):
        config = Configuration.objects.create(
            key="numbering_sequences",
            field="all_sequences",
            invoice_number_sequence="INV-{year}-{counter:05d}",
            estimate_number_sequence="EST-{year}-{counter:05d}",
            job_number_sequence="JOB-{year}-{counter:05d}",
            po_number_sequence="PO-{year}-{counter:05d}"
        )
        
        self.assertIn("{year}", config.invoice_number_sequence)
        self.assertIn("{counter:", config.invoice_number_sequence)
        self.assertIn("{year}", config.estimate_number_sequence)
        self.assertIn("{year}", config.job_number_sequence)
        self.assertIn("{year}", config.po_number_sequence)

    def test_model_cascade_deletions(self):
        job = Job.objects.create(
            job_number="JOB006",
            contact=self.contact
        )
        
        work_order = WorkOrder.objects.create(job=job)
        task = Task.objects.create(work_order=work_order, name="Test Task")
        blep = Blep.objects.create(task=task, user=self.user)
        
        initial_blep_count = Blep.objects.count()
        initial_task_count = Task.objects.count()
        
        work_order.delete()
        
        self.assertEqual(Blep.objects.count(), initial_blep_count - 1)
        self.assertEqual(Task.objects.count(), initial_task_count - 1)

    def test_user_group_relationship(self):
        group_count_before = Group.objects.count()
        user_count_before = User.objects.count()
        
        new_group = Group.objects.create(name="Developer")
        developer_user = User.objects.create_user(
            username="developer"
        )
        developer_user.groups.add(new_group)
        
        self.assertEqual(Group.objects.count(), group_count_before + 1)
        self.assertEqual(User.objects.count(), user_count_before + 1)
        self.assertIn(new_group, developer_user.groups.all())
        
        new_group.delete()
        developer_user.refresh_from_db()
        self.assertNotIn(new_group, developer_user.groups.all())

    def test_price_calculation_accuracy(self):
        price_list_item = PriceListItem.objects.create(
            code="BOLT001",
            purchase_price=Decimal('1.50'),
            selling_price=Decimal('2.25'),
            qty_on_hand=Decimal('100.00')
        )
        
        # Create an invoice for testing
        job = Job.objects.create(job_number="CALC_TEST", contact=self.contact)
        invoice = Invoice.objects.create(job=job, invoice_number="INV_CALC")
        
        line_item = InvoiceLineItem.objects.create(
            invoice=invoice,
            price_list_item=price_list_item,
            qty=Decimal('10.00'),
            price_currency=Decimal('22.50')
        )
        
        expected_total = line_item.qty * price_list_item.selling_price
        self.assertEqual(line_item.price_currency, expected_total)

    def test_unique_constraints(self):
        job = Job.objects.create(job_number="UNIQUE001", contact=self.contact)
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Job.objects.create(job_number="UNIQUE001", contact=self.contact)
        
        invoice = Invoice.objects.create(
            job=job,
            invoice_number="INV_UNIQUE001"
        )
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Invoice.objects.create(
                    job=job,
                    invoice_number="INV_UNIQUE001"
                )

    def test_model_str_representations(self):
        job = Job.objects.create(job_number="STR_TEST", contact=self.contact)
        estimate = Estimate.objects.create(job=job, estimate_number="EST_STR")
        invoice = Invoice.objects.create(job=job, invoice_number="INV_STR")
        po = PurchaseOrder.objects.create(po_number="PO_STR")
        
        self.assertEqual(str(job), "Job STR_TEST")
        self.assertEqual(str(estimate), "Estimate EST_STR")
        self.assertEqual(str(invoice), "Invoice INV_STR")
        self.assertEqual(str(po), "PO PO_STR")
        self.assertEqual(str(self.group), "Manager")
        self.assertEqual(str(self.contact), "Test Contact")


class LineItemValidationTest(TestCase):
    """Test LineItem validation across all submodel types"""
    
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="VALID_JOB001",
            contact=self.contact,
            description="Test job for validation"
        )
        
        # Create related objects
        self.estimate = Estimate.objects.create(
            job=self.job,
            estimate_number="EST_VALID001"
        )
        self.invoice = Invoice.objects.create(
            job=self.job,
            invoice_number="INV_VALID001"
        )
        self.purchase_order = PurchaseOrder.objects.create(
            job=self.job,
            po_number="PO_VALID001"
        )
        self.bill = Bill.objects.create(
            purchase_order=self.purchase_order,
            contact=self.contact,
            vendor_invoice_number="VIN_VALID001"
        )
        self.work_order = WorkOrder.objects.create(job=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
        )
        
        # Create price list item
        self.price_list_item = PriceListItem.objects.create(
            code="TEST001",
            selling_price=Decimal('25.00')
        )
    
    def test_estimate_line_item_validation_both_null_allowed(self):
        """Test EstimateLineItem allows both task and price_list_item to be null"""
        line_item = EstimateLineItem.objects.create(
            estimate=self.estimate,
            task=None,
            price_list_item=None,
            description="No task or price item"
        )
        line_item.full_clean()  # Should not raise
        self.assertIsNone(line_item.task)
        self.assertIsNone(line_item.price_list_item)
    
    def test_estimate_line_item_validation_cannot_have_both(self):
        """Test EstimateLineItem cannot have both task and price_list_item"""
        line_item = EstimateLineItem(
            estimate=self.estimate,
            task=self.task,
            price_list_item=self.price_list_item,
            description="Invalid - has both"
        )
        with self.assertRaises(ValidationError) as context:
            line_item.full_clean()
        self.assertIn("cannot have both task and price_list_item", str(context.exception))
    
    def test_purchase_order_line_item_validation_both_null_allowed(self):
        """Test PurchaseOrderLineItem allows both task and price_list_item to be null"""
        line_item = PurchaseOrderLineItem.objects.create(
            purchase_order=self.purchase_order,
            task=None,
            price_list_item=None,
            description="No task or price item"
        )
        line_item.full_clean()  # Should not raise
        self.assertIsNone(line_item.task)
        self.assertIsNone(line_item.price_list_item)
    
    def test_purchase_order_line_item_validation_cannot_have_both(self):
        """Test PurchaseOrderLineItem cannot have both task and price_list_item"""
        line_item = PurchaseOrderLineItem(
            purchase_order=self.purchase_order,
            task=self.task,
            price_list_item=self.price_list_item,
            description="Invalid - has both"
        )
        with self.assertRaises(ValidationError) as context:
            line_item.full_clean()
        self.assertIn("cannot have both task and price_list_item", str(context.exception))
    
    def test_bill_line_item_validation_both_null_allowed(self):
        """Test BillLineItem allows both task and price_list_item to be null"""
        line_item = BillLineItem.objects.create(
            bill=self.bill,
            task=None,
            price_list_item=None,
            description="No task or price item"
        )
        line_item.full_clean()  # Should not raise
        self.assertIsNone(line_item.task)
        self.assertIsNone(line_item.price_list_item)
    
    def test_bill_line_item_validation_cannot_have_both(self):
        """Test BillLineItem cannot have both task and price_list_item"""
        line_item = BillLineItem(
            bill=self.bill,
            task=self.task,
            price_list_item=self.price_list_item,
            description="Invalid - has both"
        )
        with self.assertRaises(ValidationError) as context:
            line_item.full_clean()
        self.assertIn("cannot have both task and price_list_item", str(context.exception))
