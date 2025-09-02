from django.test import TestCase, TransactionTestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction, IntegrityError
from decimal import Decimal
from datetime import timedelta
from apps.contacts.models import Contact, Business, PaymentTerms
from apps.core.models import User, Role, Configuration
from apps.jobs.models import Job, Estimate, WorkOrder, Task, Step, TaskMapping
from apps.invoicing.models import Invoice, LineItem, PriceListItem, ItemType
from apps.purchasing.models import PurchaseOrder, Bill


class ComprehensiveModelIntegrationTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(role_name="Manager", role_description="Manager role")
        self.user = User.objects.create_user(username="testuser", email="test@example.com", role_id=self.role)
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
            term_id=self.payment_terms
        )

    def test_complete_job_workflow(self):
        job = Job.objects.create(
            job_number="JOB001",
            status='draft',
            contact_id=self.contact,
            description="Test job description"
        )
        
        estimate = Estimate.objects.create(
            job_id=job,
            estimate_number="EST001",
            revision_number=1,
            status='open'
        )
        
        work_order = WorkOrder.objects.create(
            job_id=job,
            status='incomplete',
            estimated_time=timedelta(hours=8)
        )
        
        task = Task.objects.create(
            assigned_id=self.user,
            work_order_id=work_order,
            name="Test Task",
            task_type="Development"
        )
        
        step = Step.objects.create(
            user_id=self.user,
            task_id=task,
            start_time=timezone.now()
        )
        
        self.assertEqual(job.status, 'draft')
        self.assertEqual(estimate.job_id, job)
        self.assertEqual(work_order.job_id, job)
        self.assertEqual(task.work_order_id, work_order)
        self.assertEqual(step.task_id, task)

    def test_invoice_line_item_workflow(self):
        job = Job.objects.create(
            job_number="JOB002",
            contact_id=self.contact
        )
        
        estimate = Estimate.objects.create(
            job_id=job,
            estimate_number="EST002"
        )
        
        invoice = Invoice.objects.create(
            job_id=job,
            invoice_number="INV001"
        )
        
        item_type = ItemType.objects.create(
            name="Test Item Type",
            taxability="taxable"
        )
        
        price_list_item = PriceListItem.objects.create(
            item_type_id=item_type,
            code="ITEM001",
            description="Test item",
            purchase_price=Decimal('10.00'),
            selling_price=Decimal('15.00')
        )
        
        line_item = LineItem.objects.create(
            estimate_id=estimate,
            invoice_id=invoice,
            price_list_item_id=price_list_item,
            qty=Decimal('5.00'),
            description="Test line item",
            price_currency=Decimal('75.00')
        )
        
        self.assertEqual(line_item.estimate_id, estimate)
        self.assertEqual(line_item.invoice_id, invoice)
        self.assertEqual(line_item.price_list_item_id, price_list_item)
        self.assertEqual(line_item.qty, Decimal('5.00'))

    def test_purchase_order_workflow(self):
        job = Job.objects.create(
            job_number="JOB003",
            contact_id=self.contact
        )
        
        purchase_order = PurchaseOrder.objects.create(
            job_id=job,
            po_number="PO001"
        )
        
        bill = Bill.objects.create(
            po_id=purchase_order,
            contact_id=self.contact,
            vendor_invoice_number="VENDOR001"
        )
        
        line_item = LineItem.objects.create(
            po_id=purchase_order,
            bill_id=bill,
            qty=Decimal('2.00'),
            description="Purchase item",
            price_currency=Decimal('50.00')
        )
        
        self.assertEqual(bill.po_id, purchase_order)
        self.assertEqual(line_item.po_id, purchase_order)
        self.assertEqual(line_item.bill_id, bill)

    def test_estimate_superseding(self):
        job = Job.objects.create(
            job_number="JOB004",
            contact_id=self.contact
        )
        
        original_estimate = Estimate.objects.create(
            job_id=job,
            estimate_number="EST003",
            revision_number=1,
            status='open'
        )
        
        superseding_estimate = Estimate.objects.create(
            job_id=job,
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

    def test_task_hierarchy_workflow(self):
        job = Job.objects.create(
            job_number="JOB005",
            contact_id=self.contact
        )
        
        work_order = WorkOrder.objects.create(job_id=job)
        
        parent_task = Task.objects.create(
            work_order_id=work_order,
            name="Parent Task",
            task_type="Planning"
        )
        
        child_work_order = WorkOrder.objects.create(
            job_id=job,
            parent_task_id=parent_task
        )
        
        child_task = Task.objects.create(
            work_order_id=child_work_order,
            name="Child Task",
            task_type="Implementation"
        )
        
        task_mapping = TaskMapping.objects.create(
            task_id=parent_task,
            step_type="Planning",
            task_type_id="PLAN001",
            breakdown_of_task="Break down the planning requirements"
        )
        
        self.assertEqual(child_work_order.parent_task_id, parent_task)
        self.assertEqual(task_mapping.task_id, parent_task)

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
            contact_id=self.contact
        )
        
        work_order = WorkOrder.objects.create(job_id=job)
        task = Task.objects.create(work_order_id=work_order, name="Test Task", task_type="Test")
        step = Step.objects.create(task_id=task, user_id=self.user)
        
        initial_step_count = Step.objects.count()
        initial_task_count = Task.objects.count()
        
        work_order.delete()
        
        self.assertEqual(Step.objects.count(), initial_step_count - 1)
        self.assertEqual(Task.objects.count(), initial_task_count - 1)

    def test_user_role_relationship(self):
        role_count_before = Role.objects.count()
        user_count_before = User.objects.count()
        
        new_role = Role.objects.create(role_name="Developer")
        developer_user = User.objects.create_user(
            username="developer",
            role_id=new_role
        )
        
        self.assertEqual(Role.objects.count(), role_count_before + 1)
        self.assertEqual(User.objects.count(), user_count_before + 1)
        self.assertEqual(developer_user.role_id, new_role)
        
        new_role.delete()
        developer_user.refresh_from_db()
        self.assertIsNone(developer_user.role_id)

    def test_price_calculation_accuracy(self):
        item_type = ItemType.objects.create(name="Hardware")
        
        price_list_item = PriceListItem.objects.create(
            item_type_id=item_type,
            code="BOLT001",
            purchase_price=Decimal('1.50'),
            selling_price=Decimal('2.25'),
            qty_on_hand=Decimal('100.00')
        )
        
        line_item = LineItem.objects.create(
            price_list_item_id=price_list_item,
            qty=Decimal('10.00'),
            price_currency=Decimal('22.50')
        )
        
        expected_total = line_item.qty * price_list_item.selling_price
        self.assertEqual(line_item.price_currency, expected_total)

    def test_unique_constraints(self):
        job = Job.objects.create(job_number="UNIQUE001", contact_id=self.contact)
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Job.objects.create(job_number="UNIQUE001", contact_id=self.contact)
        
        invoice = Invoice.objects.create(
            job_id=job,
            invoice_number="INV_UNIQUE001"
        )
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Invoice.objects.create(
                    job_id=job,
                    invoice_number="INV_UNIQUE001"
                )

    def test_model_str_representations(self):
        job = Job.objects.create(job_number="STR_TEST", contact_id=self.contact)
        estimate = Estimate.objects.create(job_id=job, estimate_number="EST_STR")
        invoice = Invoice.objects.create(job_id=job, invoice_number="INV_STR")
        po = PurchaseOrder.objects.create(po_number="PO_STR")
        
        self.assertEqual(str(job), "Job STR_TEST")
        self.assertEqual(str(estimate), "Estimate EST_STR")
        self.assertEqual(str(invoice), "Invoice INV_STR")
        self.assertEqual(str(po), "PO PO_STR")
        self.assertEqual(str(self.role), "Manager")
        self.assertEqual(str(self.contact), "Test Contact")