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
    
    def save(self, *args, **kwargs):
        """Override save to detect status changes and send signals if needed."""
        old_status = None
        
        # Check if this is an update (not a new object)
        if self.pk:
            try:
                # Fetch only the status field to minimize DB load
                old_status = Estimate.objects.only('status').get(pk=self.pk).status
            except Estimate.DoesNotExist:
                pass
        
        # Call parent save
        super().save(*args, **kwargs)
        
        # Check if status changed and handle worksheet updates
        if old_status and old_status != self.status:
            self._maybe_update_worksheet_statuses(old_status)
    
    def _maybe_update_worksheet_statuses(self, old_status):
        """Send signal to update worksheet statuses if the change is relevant."""
        # Map statuses to worksheet statuses (pure Python, no DB hit)
        old_ws_status = self._get_worksheet_status(old_status)
        new_ws_status = self._get_worksheet_status(self.status)
        
        # Only send signal if worksheet status should change
        if old_ws_status != new_ws_status and new_ws_status is not None:
            from apps.jobs.signals import estimate_status_changed_for_worksheet
            estimate_status_changed_for_worksheet.send(
                sender=self.__class__,
                estimate=self,
                new_worksheet_status=new_ws_status
            )
    
    def _get_worksheet_status(self, estimate_status):
        """Map estimate status to worksheet status."""
        if estimate_status == 'draft':
            return 'draft'
        elif estimate_status in ['open', 'accepted', 'rejected']:
            return 'final'
        elif estimate_status == 'superseded':
            return 'superseded'
        return None

    def __str__(self):
        return f"Estimate {self.estimate_number}"
    
    class Meta:
        unique_together = ['estimate_number', 'revision_number']


class AbstractWorkContainer(models.Model):
    """Abstract base class for WorkOrder and EstWorksheet containing common fields."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    template = models.ForeignKey('WorkOrderTemplate', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        abstract = True


class WorkOrder(AbstractWorkContainer):
    WORK_ORDER_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('incomplete', 'Incomplete'),
        ('blocked', 'Blocked'),
        ('complete', 'Complete'),
    ]

    work_order_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=20, choices=WORK_ORDER_STATUS_CHOICES, default='draft')

    def __str__(self):
        return f"Work Order {self.pk}"


class EstWorksheet(AbstractWorkContainer):
    EST_WORKSHEET_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('final', 'Final'),
        ('superseded', 'Superseded'),
    ]

    est_worksheet_id = models.AutoField(primary_key=True)
    estimate = models.ForeignKey(Estimate, on_delete=models.SET_NULL, null=True, blank=True, related_name='worksheets')
    status = models.CharField(max_length=20, choices=EST_WORKSHEET_STATUS_CHOICES, default='draft')
    version = models.IntegerField(default=1)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    created_date = models.DateTimeField(default=timezone.now)
    
    def save(self, *args, **kwargs):
        """Override save to set initial status based on Estimate if creating new worksheet."""
        # Only set status from estimate on creation, not updates
        if not self.pk and self.estimate:
            if self.estimate.status == 'draft':
                self.status = 'draft'
            elif self.estimate.status in ['open', 'accepted', 'rejected']:
                self.status = 'final'
            elif self.estimate.status == 'superseded':
                self.status = 'superseded'
        super().save(*args, **kwargs)
    
    def create_new_version(self):
        """Create a new version of this worksheet, marking this one as superseded."""
        # Mark current worksheet as superseded
        self.status = 'superseded'
        self.save()
        
        # Create new worksheet with this one as parent
        new_worksheet = EstWorksheet.objects.create(
            job=self.job,
            template=self.template,
            status='draft',
            version=self.version + 1,
            parent=self,  # New worksheet points to this one as parent
            estimate=None  # New version starts without an estimate
        )
        
        # Copy all tasks to the new worksheet
        for task in self.task_set.all():
            Task.objects.create(
                parent_task=task.parent_task,
                assignee=task.assignee,
                est_worksheet=new_worksheet,
                name=task.name,
                units=task.units,
                rate=task.rate,
                est_qty=task.est_qty,
                template=task.template
            )
        
        return new_worksheet
    
    def __str__(self):
        return f"EstWorksheet {self.pk} v{self.version}"


class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    parent_task = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks')
    assignee = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, null=True, blank=True)
    est_worksheet = models.ForeignKey(EstWorksheet, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    units = models.CharField(max_length=50, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    est_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    template = models.ForeignKey('TaskTemplate', on_delete=models.SET_NULL, null=True, blank=True)
    
    def clean(self):
        """Ensure task is attached to either WorkOrder or EstWorksheet, but not both."""
        from django.core.exceptions import ValidationError
        if self.work_order and self.est_worksheet:
            raise ValidationError("Task cannot be attached to both WorkOrder and EstWorksheet")
        if not self.work_order and not self.est_worksheet:
            raise ValidationError("Task must be attached to either WorkOrder or EstWorksheet")
    
    def get_container(self):
        """Return the container (WorkOrder or EstWorksheet) this task belongs to."""
        return self.work_order or self.est_worksheet

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
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    step_type = models.CharField(max_length=100)
    task_type_id = models.CharField(max_length=50)
    breakdown_of_task = models.TextField(blank=True)

    def __str__(self):
        return f"Task Mapping {self.pk}"


from apps.core.models import BaseLineItem


class WorkOrderTemplate(models.Model):
    """Template for creating WorkOrders with predefined TaskTemplates."""
    
    template_id = models.AutoField(primary_key=True)
    template_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.template_name
        
    def generate_work_order(self, job):
        """Generate a WorkOrder from this template for the given job."""
        # Implementation will be in service class
        pass


class TaskTemplate(models.Model):
    """Template for creating Tasks with predefined settings."""
    
    template_id = models.AutoField(primary_key=True)
    template_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    units = models.CharField(max_length=50, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    est_qty = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    task_mapping = models.ForeignKey(TaskMapping, on_delete=models.CASCADE, null=True, blank=True)
    work_order_template = models.ForeignKey(WorkOrderTemplate, on_delete=models.CASCADE, null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.template_name
        
    def generate_task(self, work_order, assignee=None):
        """Generate a Task from this template for the given work_order."""
        # Implementation will be in service class
        pass


class EstimateLineItem(BaseLineItem):
    """Line item for estimates - inherits shared functionality from BaseLineItem."""
    
    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Estimate Line Item"
        verbose_name_plural = "Estimate Line Items"
    
    def __str__(self):
        return f"Estimate Line Item {self.pk} for {self.estimate.estimate_number}"
