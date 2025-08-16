from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.jobs.models import Job, Estimate, WorkOrder, Task, Step, TaskMapping
from apps.contacts.models import Contact
from apps.core.models import User
from .base import FixtureTestCase


class JobModelFixtureTest(FixtureTestCase):
    """
    Test Job model using fixture data loaded from unit_test_data.json
    """
    
    def test_jobs_exist_from_fixture(self):
        """Test that jobs from fixture data exist and have correct properties"""
        job1 = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(job1.status, "draft")
        self.assertEqual(job1.description, "Kitchen renovation project for residential client")
        self.assertIsNone(job1.completion_date)
        self.assertEqual(job1.contact_id.name, "John Doe")
        
        job2 = Job.objects.get(job_number="JOB-2024-0002")
        self.assertEqual(job2.status, "complete")
        self.assertEqual(job2.description, "Office electrical upgrade")
        self.assertIsNotNone(job2.completion_date)
        self.assertEqual(job2.contact_id.name, "Jane Smith")
        
    def test_job_str_method_with_fixture_data(self):
        """Test job string representation with fixture data"""
        job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(str(job), "Job JOB-2024-0001")
        
    def test_job_contact_relationships(self):
        """Test that jobs are properly linked to contacts"""
        job1 = Job.objects.get(job_number="JOB-2024-0001")
        contact1 = Contact.objects.get(name="John Doe")
        self.assertEqual(job1.contact_id, contact1)
        
    def test_job_status_progression(self):
        """Test updating job status using fixture data"""
        job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(job.status, "draft")
        
        job.status = "approved"
        job.save()
        
        updated_job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(updated_job.status, "approved")
        
    def test_create_new_job_with_existing_contact(self):
        """Test creating a new job with existing contact from fixtures"""
        contact = Contact.objects.get(name="John Doe")
        new_job = Job.objects.create(
            job_number="JOB-2024-0003",
            contact_id=contact,
            description="New project for existing customer",
            status="draft"
        )
        self.assertEqual(new_job.contact_id, contact)
        self.assertEqual(Job.objects.count(), 3)  # 2 from fixture + 1 new


class EstimateModelFixtureTest(FixtureTestCase):
    """
    Test Estimate model using fixture data
    """
    
    def test_estimates_exist_from_fixture(self):
        """Test that estimates from fixture data exist and have correct properties"""
        est1 = Estimate.objects.get(estimate_number="EST-2024-0001")
        self.assertEqual(est1.revision_number, 1)
        self.assertEqual(est1.status, "draft")
        self.assertEqual(est1.job_id.job_number, "JOB-2024-0001")
        
        est2 = Estimate.objects.get(estimate_number="EST-2024-0002")
        self.assertEqual(est2.revision_number, 2)
        self.assertEqual(est2.status, "accepted")
        self.assertEqual(est2.job_id.job_number, "JOB-2024-0002")
        
    def test_estimate_str_method_with_fixture_data(self):
        """Test estimate string representation with fixture data"""
        estimate = Estimate.objects.get(estimate_number="EST-2024-0001")
        self.assertEqual(str(estimate), "Estimate EST-2024-0001")
        
    def test_estimate_job_relationships(self):
        """Test that estimates are properly linked to jobs"""
        estimate = Estimate.objects.get(estimate_number="EST-2024-0001")
        job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(estimate.job_id, job)


class WorkOrderModelFixtureTest(FixtureTestCase):
    """
    Test WorkOrder model using fixture data
    """
    
    def test_work_orders_exist_from_fixture(self):
        """Test that work orders from fixture data exist and have correct properties"""
        wo1 = WorkOrder.objects.get(pk=1)
        self.assertEqual(wo1.status, "incomplete")
        self.assertEqual(wo1.job_id.job_number, "JOB-2024-0001")
        self.assertEqual(wo1.estimated_time, timedelta(hours=40))
        
        wo2 = WorkOrder.objects.get(pk=2)
        self.assertEqual(wo2.status, "complete")
        self.assertEqual(wo2.job_id.job_number, "JOB-2024-0002")
        self.assertEqual(wo2.estimated_time, timedelta(hours=24))
        
    def test_work_order_str_method_with_fixture_data(self):
        """Test work order string representation with fixture data"""
        work_order = WorkOrder.objects.get(pk=1)
        self.assertEqual(str(work_order), "Work Order 1")
        
    def test_work_order_job_relationships(self):
        """Test that work orders are properly linked to jobs"""
        work_order = WorkOrder.objects.get(pk=1)
        job = Job.objects.get(job_number="JOB-2024-0001")
        self.assertEqual(work_order.job_id, job)


class TaskModelFixtureTest(FixtureTestCase):
    """
    Test Task model using fixture data
    """
    
    def test_tasks_exist_from_fixture(self):
        """Test that tasks from fixture data exist and have correct properties"""
        task1 = Task.objects.get(name="Kitchen demolition")
        self.assertEqual(task1.pre_submitted_id, "PRE001")
        self.assertEqual(task1.task_type, "demolition")
        self.assertEqual(task1.assigned_id.username, "manager1")
        self.assertEqual(task1.work_order_id.pk, 1)
        
        task2 = Task.objects.get(name="Electrical rough-in")
        self.assertEqual(task2.pre_submitted_id, "PRE002")
        self.assertEqual(task2.task_type, "electrical")
        self.assertEqual(task2.assigned_id.username, "manager1")
        
    def test_task_str_method_with_fixture_data(self):
        """Test task string representation with fixture data"""
        task = Task.objects.get(name="Kitchen demolition")
        self.assertEqual(str(task), "Kitchen demolition")
        
    def test_task_user_relationships(self):
        """Test that tasks are properly assigned to users"""
        task = Task.objects.get(name="Kitchen demolition")
        user = User.objects.get(username="manager1")
        self.assertEqual(task.assigned_id, user)
        
    def test_task_work_order_relationships(self):
        """Test that tasks are properly linked to work orders"""
        task = Task.objects.get(name="Kitchen demolition")
        work_order = WorkOrder.objects.get(pk=1)
        self.assertEqual(task.work_order_id, work_order)
        
    def test_create_new_task_for_existing_work_order(self):
        """Test creating a new task for existing work order from fixtures"""
        work_order = WorkOrder.objects.get(pk=1)
        user = User.objects.get(username="manager1")
        
        new_task = Task.objects.create(
            pre_submitted_id="PRE003",
            assigned_id=user,
            work_order_id=work_order,
            name="Cabinet installation",
            task_type="installation"
        )
        self.assertEqual(new_task.work_order_id, work_order)
        self.assertEqual(Task.objects.count(), 3)  # 2 from fixture + 1 new


class StepModelFixtureTest(FixtureTestCase):
    """
    Test Step model using fixture data
    """
    
    def test_create_step_for_existing_task(self):
        """Test creating steps for existing tasks from fixtures"""
        task = Task.objects.get(name="Kitchen demolition")
        user = User.objects.get(username="manager1")
        
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=4)
        
        step = Step.objects.create(
            user_id=user,
            task_id=task,
            start_time=start_time,
            end_time=end_time
        )
        
        self.assertEqual(step.task_id, task)
        self.assertEqual(step.user_id, user)
        self.assertEqual(step.start_time, start_time)
        self.assertEqual(step.end_time, end_time)
        
    def test_step_str_method_with_fixture_task(self):
        """Test step string representation with fixture task data"""
        task = Task.objects.get(name="Kitchen demolition")
        step = Step.objects.create(task_id=task)
        expected_str = f"Step {step.step_id} for Task {task.task_id}"
        self.assertEqual(str(step), expected_str)


class TaskMappingModelFixtureTest(FixtureTestCase):
    """
    Test TaskMapping model using fixture data
    """
    
    def test_create_task_mapping_for_existing_task(self):
        """Test creating task mapping for existing task from fixtures"""
        task = Task.objects.get(name="Kitchen demolition")
        
        mapping = TaskMapping.objects.create(
            task_id=task,
            step_type="preparation",
            task_type_id="DEMO_PREP_001",
            breakdown_of_task="Remove cabinet doors and drawers, disconnect utilities"
        )
        
        self.assertEqual(mapping.task_id, task)
        self.assertEqual(mapping.step_type, "preparation")
        self.assertEqual(mapping.task_type_id, "DEMO_PREP_001")
        self.assertEqual(mapping.breakdown_of_task, "Remove cabinet doors and drawers, disconnect utilities")
        
    def test_task_mapping_str_method_with_fixture_task(self):
        """Test task mapping string representation with fixture task data"""
        task = Task.objects.get(name="Kitchen demolition")
        mapping = TaskMapping.objects.create(
            task_id=task,
            step_type="execution",
            task_type_id="DEMO_EXEC_001"
        )
        expected_str = f"Task Mapping {mapping.task_mapping_id}"
        self.assertEqual(str(mapping), expected_str)