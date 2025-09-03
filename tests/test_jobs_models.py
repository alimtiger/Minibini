from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.jobs.models import Job, Estimate, WorkOrder, Task, Step, TaskMapping
from apps.contacts.models import Contact
from apps.core.models import User


class JobModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        
    def test_job_creation(self):
        job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact,
            description="Test job description",
            status='draft'
        )
        self.assertEqual(job.job_number, "JOB001")
        self.assertEqual(job.contact_id, self.contact)
        self.assertEqual(job.description, "Test job description")
        self.assertEqual(job.status, 'draft')
        self.assertIsNotNone(job.created_date)
        
    def test_job_str_method(self):
        job = Job.objects.create(
            job_number="JOB002",
            contact_id=self.contact
        )
        self.assertEqual(str(job), "Job JOB002")
        
    def test_job_default_values(self):
        job = Job.objects.create(
            job_number="JOB003",
            contact_id=self.contact
        )
        self.assertEqual(job.status, 'draft')
        self.assertIsNone(job.completion_date)
        
    def test_job_status_choices(self):
        statuses = ['draft', 'needs_attention', 'approved', 'rejected', 'blocked', 'complete']
        for status in statuses:
            job = Job.objects.create(
                job_number=f"JOB_{status}",
                contact_id=self.contact,
                status=status
            )
            self.assertEqual(job.status, status)
            
    def test_job_with_completion_date(self):
        completion_time = timezone.now()
        job = Job.objects.create(
            job_number="JOB004",
            contact_id=self.contact,
            completion_date=completion_time,
            status='complete'
        )
        self.assertEqual(job.completion_date, completion_time)


class EstimateModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact
        )
        
    def test_estimate_creation(self):
        estimate = Estimate.objects.create(
            job_id=self.job,
            estimate_number="EST001",
            revision_number=2,
            status='open'
        )
        self.assertEqual(estimate.job_id, self.job)
        self.assertEqual(estimate.estimate_number, "EST001")
        self.assertEqual(estimate.revision_number, 2)
        self.assertEqual(estimate.status, 'open')
        
    def test_estimate_str_method(self):
        estimate = Estimate.objects.create(
            job_id=self.job,
            estimate_number="EST002"
        )
        self.assertEqual(str(estimate), "Estimate EST002")
        
    def test_estimate_defaults(self):
        estimate = Estimate.objects.create(
            job_id=self.job,
            estimate_number="EST003"
        )
        self.assertEqual(estimate.revision_number, 1)
        self.assertEqual(estimate.status, 'draft')
        
    def test_estimate_status_choices(self):
        statuses = ['draft', 'open', 'accepted', 'rejected']
        for status in statuses:
            estimate = Estimate.objects.create(
                job_id=self.job,
                estimate_number=f"EST_{status}",
                status=status
            )
            self.assertEqual(estimate.status, status)


class WorkOrderModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact
        )
        self.work_order = WorkOrder.objects.create(job_id=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Parent Task",
            task_type="parent"
        )
        
    def test_work_order_creation(self):
        work_order = WorkOrder.objects.create(
            job_id=self.job,
            status='blocked',
            estimated_time=timedelta(hours=8)
        )
        self.assertEqual(work_order.job_id, self.job)
        self.assertEqual(work_order.status, 'blocked')
        self.assertEqual(work_order.estimated_time, timedelta(hours=8))
        
    def test_work_order_str_method(self):
        work_order = WorkOrder.objects.create(job_id=self.job)
        self.assertEqual(str(work_order), f"Work Order {work_order.pk}")
        
    def test_work_order_defaults(self):
        work_order = WorkOrder.objects.create(job_id=self.job)
        self.assertEqual(work_order.status, 'incomplete')
        self.assertIsNone(work_order.estimated_time)
        
    def test_work_order_status_choices(self):
        statuses = ['incomplete', 'blocked', 'complete']
        for status in statuses:
            work_order = WorkOrder.objects.create(
                job_id=self.job,
                status=status
            )
            self.assertEqual(work_order.status, status)


class TaskModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact
        )
        self.work_order = WorkOrder.objects.create(job_id=self.job)
        self.user = User.objects.create_user(username="testuser")
        
    def test_task_creation(self):
        parent_task = Task.objects.create(
            work_order=self.work_order,
            name="Parent Task",
            task_type="parent"
        )
        task = Task.objects.create(
            parent_task=parent_task,
            assigned=self.user,
            work_order=self.work_order,
            name="Installation Task",
            task_type="installation"
        )
        self.assertEqual(task.parent_task, parent_task)
        self.assertEqual(task.assigned, self.user)
        self.assertEqual(task.work_order, self.work_order)
        self.assertEqual(task.name, "Installation Task")
        self.assertEqual(task.task_type, "installation")
        
    def test_task_str_method(self):
        task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
            task_type="test"
        )
        self.assertEqual(str(task), "Test Task")
        
    def test_task_optional_fields(self):
        task = Task.objects.create(
            work_order=self.work_order,
            name="Basic Task",
            task_type="basic"
        )
        self.assertIsNone(task.parent_task)
        self.assertIsNone(task.assigned)


class StepModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact
        )
        self.work_order = WorkOrder.objects.create(job_id=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
            task_type="test"
        )
        self.user = User.objects.create_user(username="testuser")
        
    def test_step_creation(self):
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=2)
        
        step = Step.objects.create(
            user_id=self.user,
            task_id=self.task,
            start_time=start_time,
            end_time=end_time
        )
        self.assertEqual(step.user_id, self.user)
        self.assertEqual(step.task_id, self.task)
        self.assertEqual(step.start_time, start_time)
        self.assertEqual(step.end_time, end_time)
        
    def test_step_str_method(self):
        step = Step.objects.create(task_id=self.task)
        self.assertEqual(str(step), f"Step {step.step_id} for Task {self.task.task_id}")
        
    def test_step_optional_fields(self):
        step = Step.objects.create(task_id=self.task)
        self.assertIsNone(step.user_id)
        self.assertIsNone(step.start_time)
        self.assertIsNone(step.end_time)


class TaskMappingModelTest(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(name="Test Customer")
        self.job = Job.objects.create(
            job_number="JOB001",
            contact_id=self.contact
        )
        self.work_order = WorkOrder.objects.create(job_id=self.job)
        self.task = Task.objects.create(
            work_order=self.work_order,
            name="Test Task",
            task_type="test"
        )
        
    def test_task_mapping_creation(self):
        mapping = TaskMapping.objects.create(
            task_id=self.task,
            step_type="preparation",
            task_type_id="PREP_001",
            breakdown_of_task="Detailed breakdown of preparation steps"
        )
        self.assertEqual(mapping.task_id, self.task)
        self.assertEqual(mapping.step_type, "preparation")
        self.assertEqual(mapping.task_type_id, "PREP_001")
        self.assertEqual(mapping.breakdown_of_task, "Detailed breakdown of preparation steps")
        
    def test_task_mapping_str_method(self):
        mapping = TaskMapping.objects.create(
            task_id=self.task,
            step_type="execution",
            task_type_id="EXEC_001"
        )
        self.assertEqual(str(mapping), f"Task Mapping {mapping.task_mapping_id}")
        
    def test_task_mapping_optional_breakdown(self):
        mapping = TaskMapping.objects.create(
            task_id=self.task,
            step_type="completion",
            task_type_id="COMP_001"
        )
        self.assertEqual(mapping.breakdown_of_task, "")