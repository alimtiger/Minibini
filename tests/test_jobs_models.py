from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.jobs.models import Job, Estimate, WorkOrder, Task, Blep, TaskMapping, WorkOrderTemplate, TaskTemplate
from apps.contacts.models import Contact
from apps.core.models import User


class JobModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        
    def test_job_creation(self):
        job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact,
            description="Test job description",
            status='draft'
        )
        self.assertEqual(job.job_number, "JOB001")
        self.assertEqual(job.contact, self.contact)
        self.assertEqual(job.description, "Test job description")
        self.assertEqual(job.status, 'draft')
        self.assertIsNotNone(job.created_date)
        
    def test_job_str_method(self):
        job = Job.objects.create(
            job_number="JOB002",
            contact=self.contact
        )
        self.assertEqual(str(job), "Job JOB002")
        
    def test_job_default_values(self):
        job = Job.objects.create(
            job_number="JOB003",
            contact=self.contact
        )
        self.assertEqual(job.status, 'draft')
        self.assertIsNone(job.completion_date)
        
    def test_job_status_choices(self):
        statuses = ['draft', 'needs_attention', 'approved', 'rejected', 'blocked', 'complete']
        for status in statuses:
            job = Job.objects.create(
                job_number=f"JOB_{status}",
                contact=self.contact,
                status=status
            )
            self.assertEqual(job.status, status)
            
    def test_job_with_completion_date(self):
        completion_time = timezone.now()
        job = Job.objects.create(
            job_number="JOB004",
            contact=self.contact,
            completion_date=completion_time,
            status='complete'
        )
        self.assertEqual(job.completion_date, completion_time)


class EstimateModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact
        )
        
    def test_estimate_creation(self):
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number="EST001",
            revision_number=2,
            status='open'
        )
        self.assertEqual(estimate.job, self.job)
        self.assertEqual(estimate.estimate_number, "EST001")
        self.assertEqual(estimate.revision_number, 2)
        self.assertEqual(estimate.status, 'open')
        
    def test_estimate_str_method(self):
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number="EST002"
        )
        self.assertEqual(str(estimate), "Estimate EST002")
        
    def test_estimate_defaults(self):
        estimate = Estimate.objects.create(
            job=self.job,
            estimate_number="EST003"
        )
        self.assertEqual(estimate.revision_number, 1)
        self.assertEqual(estimate.status, 'draft')
        
    def test_estimate_status_choices(self):
        statuses = ['draft', 'open', 'accepted', 'rejected']
        for status in statuses:
            estimate = Estimate.objects.create(
                job=self.job,
                estimate_number=f"EST_{status}",
                status=status
            )
            self.assertEqual(estimate.status, status)


class WorkOrderModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact
        )
        self.work_order = WorkOrder.objects.create(job=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Parent Task",
        )
        
    def test_work_order_creation(self):
        work_order = WorkOrder.objects.create(
            job=self.job,
            status='blocked',
        )
        self.assertEqual(work_order.job, self.job)
        self.assertEqual(work_order.status, 'blocked')
        
    def test_work_order_str_method(self):
        work_order = WorkOrder.objects.create(job=self.job)
        self.assertEqual(str(work_order), f"Work Order {work_order.pk}")
        
    def test_work_order_defaults(self):
        work_order = WorkOrder.objects.create(job=self.job)
        # when a WorkOrder is created based on an existing Estimate it will change to status 'incomplete' before saving
        self.assertEqual(work_order.status, 'draft')
 
    def test_work_order_status_choices(self):
        statuses = ['incomplete', 'blocked', 'complete']
        for status in statuses:
            work_order = WorkOrder.objects.create(
                job=self.job,
                status=status
            )
            self.assertEqual(work_order.status, status)


class TaskModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact
        )
        self.work_order = WorkOrder.objects.create(job=self.job)
        self.user = User.objects.create_user(username="testuser")
        
    def test_task_creation(self):
        parent_task = Task.objects.create(
            work_order=self.work_order,
            name="Parent Task",
        )
        task = Task.objects.create(
            parent_task=parent_task,
            assignee=self.user,
            work_order=self.work_order,
            name="Installation Task",
        )
        self.assertEqual(task.parent_task, parent_task)
        self.assertEqual(task.assignee, self.user)
        self.assertEqual(task.work_order, self.work_order)
        self.assertEqual(task.name, "Installation Task")
        
    def test_task_str_method(self):
        task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
        )
        self.assertEqual(str(task), "Test Task")
        
    def test_task_optional_fields(self):
        task = Task.objects.create(
            work_order=self.work_order,
            name="Basic Task",
        )
        self.assertIsNone(task.parent_task)
        self.assertIsNone(task.assignee)
    
    def test_task_new_fields(self):
        """Test the new units, rate, and est_qty fields on Task."""
        task = Task.objects.create(
            work_order=self.work_order,
            name="Labor Task",
            units="hours",
            rate=Decimal('75.50'),
            est_qty=Decimal('8.00')
        )
        self.assertEqual(task.units, "hours")
        self.assertEqual(task.rate, Decimal('75.50'))
        self.assertEqual(task.est_qty, Decimal('8.00'))
        
    def test_task_new_fields_optional(self):
        """Test that new fields are optional on Task."""
        task = Task.objects.create(
            work_order=self.work_order,
            name="Simple Task"
        )
        self.assertEqual(task.units, "")  # CharField blank=True defaults to empty string
        self.assertIsNone(task.rate)  # DecimalField null=True
        self.assertIsNone(task.est_qty)  # DecimalField null=True
        
    def test_task_calculated_total(self):
        """Test calculating total from rate and est_qty."""
        task = Task.objects.create(
            work_order=self.work_order,
            name="Material Task",
            units="sheets",
            rate=Decimal('45.00'),
            est_qty=Decimal('10.00')
        )
        # While we don't have a calculated field, this tests the values can be used for calculations
        expected_total = task.rate * task.est_qty if task.rate and task.est_qty else Decimal('0.00')
        self.assertEqual(expected_total, Decimal('450.00'))


class BlepModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact
        )
        self.work_order = WorkOrder.objects.create(job=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
        )
        self.user = User.objects.create_user(username="testuser")
        
    def test_blep_creation(self):
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=2)
        
        blep = Blep.objects.create(
            user=self.user,
            task=self.task,
            start_time=start_time,
            end_time=end_time
        )
        self.assertEqual(blep.user, self.user)
        self.assertEqual(blep.task, self.task)
        self.assertEqual(blep.start_time, start_time)
        self.assertEqual(blep.end_time, end_time)
        
    def test_blep_str_method(self):
        blep = Blep.objects.create(task=self.task)
        self.assertEqual(str(blep), f"Blep {blep.pk} for Task {self.task.pk}")
        
    def test_blep_optional_fields(self):
        blep = Blep.objects.create(task=self.task)
        self.assertIsNone(blep.user)
        self.assertIsNone(blep.start_time)
        self.assertIsNone(blep.end_time)


class TaskMappingModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact
        )
        self.work_order = WorkOrder.objects.create(job=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
        )
        
    def test_task_mapping_creation(self):
        mapping = TaskMapping.objects.create(
            task=self.task,
            step_type="preparation",
            task_type_id="PREP_001",
            breakdown_of_task="Detailed breakdown of preparation steps"
        )
        self.assertEqual(mapping.task, self.task)
        self.assertEqual(mapping.step_type, "preparation")
        self.assertEqual(mapping.task_type_id, "PREP_001")
        self.assertEqual(mapping.breakdown_of_task, "Detailed breakdown of preparation steps")
        
    def test_task_mapping_str_method(self):
        mapping = TaskMapping.objects.create(
            task=self.task,
            step_type="execution",
            task_type_id="EXEC_001"
        )
        self.assertEqual(str(mapping), f"Task Mapping {mapping.pk}")
        
    def test_task_mapping_optional_breakdown(self):
        mapping = TaskMapping.objects.create(
            task=self.task,
            step_type="completion",
            task_type_id="COMP_001"
        )
        self.assertEqual(mapping.breakdown_of_task, "")
        
    def test_task_mapping_optional_task(self):
        """Test TaskMapping with null task field."""
        mapping = TaskMapping.objects.create(
            task=None,
            step_type="general",
            task_type_id="GEN_001",
            breakdown_of_task="General task mapping without specific task"
        )
        self.assertIsNone(mapping.task)
        self.assertEqual(mapping.step_type, "general")


class WorkOrderTemplateModelTest(TestCase):
    def test_work_order_template_creation(self):
        template = WorkOrderTemplate.objects.create(
            template_name="Standard Installation",
            description="Standard installation workflow template",
            is_active=True
        )
        self.assertEqual(template.template_name, "Standard Installation")
        self.assertEqual(template.description, "Standard installation workflow template")
        self.assertTrue(template.is_active)
        self.assertIsNotNone(template.created_date)
        
    def test_work_order_template_str_method(self):
        template = WorkOrderTemplate.objects.create(
            template_name="Maintenance Template"
        )
        self.assertEqual(str(template), "Maintenance Template")
        
    def test_work_order_template_defaults(self):
        template = WorkOrderTemplate.objects.create(
            template_name="Basic Template"
        )
        self.assertTrue(template.is_active)  # Default should be True
        self.assertEqual(template.description, "")  # CharField blank=True defaults to empty
        
    def test_work_order_template_inactive(self):
        template = WorkOrderTemplate.objects.create(
            template_name="Inactive Template",
            is_active=False
        )
        self.assertFalse(template.is_active)


class TaskTemplateModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact=self.contact
        )
        self.work_order = WorkOrder.objects.create(job=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
        )
        self.task_mapping = TaskMapping.objects.create(
            task=self.task,
            step_type="test_type",
            task_type_id="TEST001"
        )
        self.work_order_template = WorkOrderTemplate.objects.create(
            template_name="Test WO Template"
        )
        
    def test_task_template_creation(self):
        template = TaskTemplate.objects.create(
            template_name="Electrical Installation",
            description="Standard electrical installation task",
            units="outlets",
            rate=Decimal('45.00'),
            est_qty=Decimal('12.00'),
            task_mapping=self.task_mapping,
            work_order_template=self.work_order_template,
            is_active=True
        )
        self.assertEqual(template.template_name, "Electrical Installation")
        self.assertEqual(template.description, "Standard electrical installation task")
        self.assertEqual(template.units, "outlets")
        self.assertEqual(template.rate, Decimal('45.00'))
        self.assertEqual(template.est_qty, Decimal('12.00'))
        self.assertEqual(template.task_mapping, self.task_mapping)
        self.assertEqual(template.work_order_template, self.work_order_template)
        self.assertTrue(template.is_active)
        self.assertIsNotNone(template.created_date)
        
    def test_task_template_str_method(self):
        template = TaskTemplate.objects.create(
            template_name="Plumbing Setup",
            task_mapping=self.task_mapping
        )
        self.assertEqual(str(template), "Plumbing Setup")
        
    def test_task_template_defaults(self):
        template = TaskTemplate.objects.create(
            template_name="Default Template",
            task_mapping=self.task_mapping
        )
        self.assertTrue(template.is_active)
        self.assertEqual(template.description, "")
        self.assertEqual(template.units, "")
        self.assertIsNone(template.rate)
        self.assertIsNone(template.est_qty)
        self.assertIsNone(template.work_order_template)
    
    def test_task_template_without_task_mapping(self):
        """Test TaskTemplate can be created without TaskMapping."""
        template = TaskTemplate.objects.create(
            template_name="Template Without Mapping",
            description="Template without task mapping",
            units="hours",
            rate=Decimal('50.00'),
            est_qty=Decimal('8.00')
        )
        self.assertIsNone(template.task_mapping)
        self.assertEqual(template.template_name, "Template Without Mapping")
        self.assertEqual(template.units, "hours")
        self.assertEqual(template.rate, Decimal('50.00'))
        
    def test_task_template_new_fields_optional(self):
        """Test that new pricing fields are optional."""
        template = TaskTemplate.objects.create(
            template_name="Simple Template",
            task_mapping=self.task_mapping
        )
        self.assertEqual(template.units, "")
        self.assertIsNone(template.rate)
        self.assertIsNone(template.est_qty)
        
    def test_task_template_pricing_calculation(self):
        """Test using TaskTemplate fields for cost calculations."""
        template = TaskTemplate.objects.create(
            template_name="Material Template",
            task_mapping=self.task_mapping,
            units="square_feet",
            rate=Decimal('15.25'),
            est_qty=Decimal('200.00')
        )
        
        estimated_cost = template.rate * template.est_qty if template.rate and template.est_qty else Decimal('0.00')
        self.assertEqual(estimated_cost, Decimal('3050.00'))
        
    def test_task_template_without_work_order_template(self):
        """Test TaskTemplate can exist without WorkOrderTemplate."""
        template = TaskTemplate.objects.create(
            template_name="Standalone Template",
            task_mapping=self.task_mapping,
            work_order_template=None
        )
        self.assertIsNone(template.work_order_template)
        self.assertEqual(template.task_mapping, self.task_mapping)
