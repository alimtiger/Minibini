from django.db import models
from django.utils import timezone


class Job(models.Model):
    JOB_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('needs_attention', 'Needs Attention'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('blocked', 'Blocked'),
        ('complete', 'Complete'),
    ]

    job_id = models.AutoField(primary_key=True)
    job_number = models.CharField(max_length=50, unique=True)
    created_date = models.DateTimeField(default=timezone.now)
    completion_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=JOB_STATUS_CHOICES, default='draft')
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    customer_po_number = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Job {self.job_number}"


class Estimate(models.Model):
    ESTIMATE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('superseded', 'Superseded'),
    ]

    estimate_id = models.AutoField(primary_key=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    estimate_number = models.CharField(max_length=50)
    revision_number = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=ESTIMATE_STATUS_CHOICES, default='draft')
    superseded_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='supersedes')
    created_date = models.DateTimeField(default=timezone.now)
    superseded_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Estimate {self.estimate_number}"
    
    class Meta:
        unique_together = ['estimate_number', 'revision_number']


class WorkOrder(models.Model):
    WORK_ORDER_STATUS_CHOICES = [
        ('incomplete', 'Incomplete'),
        ('blocked', 'Blocked'),
        ('complete', 'Complete'),
    ]

    work_order_id = models.AutoField(primary_key=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=WORK_ORDER_STATUS_CHOICES, default='incomplete')
    estimated_time = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"Work Order {self.pk}"


class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks')
    assignee = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    task_type = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Blep(models.Model):
    blep_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Blep {self.pk} for Task {self.task.pk}"


class TaskMapping(models.Model):
    task_mapping_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    step_type = models.CharField(max_length=100)
    task_type_id = models.CharField(max_length=50)
    breakdown_of_task = models.TextField(blank=True)

    def __str__(self):
        return f"Task Mapping {self.task_mapping_id}"


from apps.core.models import BaseLineItem


class EstimateLineItem(BaseLineItem):
    """Line item for estimates - inherits shared functionality from BaseLineItem."""
    
    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Estimate Line Item"
        verbose_name_plural = "Estimate Line Items"
    
    def __str__(self):
        return f"Estimate Line Item {self.line_item_id} for {self.estimate.estimate_number}"
