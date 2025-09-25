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
    due_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
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
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=ESTIMATE_STATUS_CHOICES, default='draft')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
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
        unique_together = ['estimate_number', 'version']


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
    
    def get_mapping_strategy(self):
        """Get the mapping strategy from template or default to direct"""
        if self.template and self.template.task_mapping:
            return self.template.task_mapping.mapping_strategy
        return 'direct'
    
    def get_step_type(self):
        """Get the step type from template or default to labor"""
        if self.template and self.template.task_mapping:
            return self.template.task_mapping.step_type
        return 'labor'
    
    def get_product_type(self):
        """Get the product type from template"""
        if self.template and self.template.task_mapping:
            return self.template.task_mapping.default_product_type
        return ''

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
    """Reusable mapping template that defines how tasks map to line items"""
    task_mapping_id = models.AutoField(primary_key=True)
    
    # What this task represents
    STEP_TYPE_CHOICES = [
        ('product', 'Complete Product'),
        ('component', 'Product Component'),
        ('labor', 'Labor/Service'),
        ('material', 'Material/Supply'),
        ('overhead', 'Overhead/Internal'),
    ]
    step_type = models.CharField(max_length=100, choices=STEP_TYPE_CHOICES)
    
    # How to map to line items
    MAPPING_STRATEGY_CHOICES = [
        ('direct', 'Direct - One task to one line item'),
        ('bundle_to_product', 'Bundle into product line item'),
        ('bundle_to_service', 'Bundle into service line item'),
        ('exclude', 'Internal only - exclude from estimate'),
    ]
    mapping_strategy = models.CharField(max_length=30, choices=MAPPING_STRATEGY_CHOICES, default='direct')
    
    # Template-level configuration
    default_product_type = models.CharField(max_length=50, blank=True)  # e.g., "table", "chair"
    
    # Line item generation
    line_item_name = models.CharField(max_length=255, blank=True)
    line_item_description = models.TextField(blank=True)
    
    # Keep existing fields
    task_type_id = models.CharField(max_length=50)
    breakdown_of_task = models.TextField(blank=True)

    def __str__(self):
        return f"{self.task_type_id} - {self.breakdown_of_task}"


class TaskInstanceMapping(models.Model):
    """Instance-specific mapping data for individual tasks"""
    task = models.OneToOneField(Task, on_delete=models.CASCADE, primary_key=True)
    
    # Instance-specific identifiers (only for bundled tasks)
    product_identifier = models.CharField(max_length=100, blank=True)  # e.g., "table_001", "chair_001"
    product_instance = models.IntegerField(null=True, blank=True)  # For multiple items (chair 1, 2, 3, 4)
    
    def __str__(self):
        return f"Instance mapping for {self.task.name}"


from apps.core.models import BaseLineItem


class WorkOrderTemplate(models.Model):
    """Template for creating WorkOrders/EstWorksheets with product structure"""
    
    template_id = models.AutoField(primary_key=True)
    template_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Product definition
    TEMPLATE_TYPE_CHOICES = [
        ('product', 'Complete Product Template'),
        ('service', 'Service Template'),
        ('process', 'Process/Workflow Template'),
    ]
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, default='product')
    product_type = models.CharField(max_length=50, blank=True)  # e.g., "table", "chair"
    
    # Pricing
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.template_name
        
    def generate_tasks_for_worksheet(self, worksheet, quantity=1):
        """Generate all tasks for a worksheet, with proper product grouping"""
        generated_tasks = []
        
        for instance in range(1, quantity + 1):
            product_identifier = f"{self.product_type}_{worksheet.est_worksheet_id}_{instance}"
            
            # Get task template associations for this work order template
            associations = TemplateTaskAssociation.objects.filter(
                work_order_template=self,
                task_template__parent_template__isnull=True,  # Root-level templates only
                task_template__is_active=True
            ).order_by('sort_order', 'task_template__template_name')
            
            for association in associations:
                task = association.task_template.generate_task(
                    worksheet,
                    est_qty=association.est_qty,
                    product_identifier=product_identifier,
                    product_instance=instance if quantity > 1 else None
                )
                generated_tasks.append(task)
        
        return generated_tasks


class TemplateTaskAssociation(models.Model):
    """Association between WorkOrderTemplate and TaskTemplate with customizable quantities"""
    work_order_template = models.ForeignKey(WorkOrderTemplate, on_delete=models.CASCADE)
    task_template = models.ForeignKey('TaskTemplate', on_delete=models.CASCADE)
    est_qty = models.DecimalField(max_digits=10, decimal_places=2)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['work_order_template', 'task_template']
        ordering = ['sort_order', 'task_template__template_name']
    
    def __str__(self):
        return f"{self.work_order_template.template_name} -> {self.task_template.template_name} ({self.est_qty})"


class TaskTemplate(models.Model):
    """Template for creating Tasks with predefined settings"""
    
    template_id = models.AutoField(primary_key=True)
    template_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    units = models.CharField(max_length=50, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Relationships
    task_mapping = models.ForeignKey(TaskMapping, on_delete=models.CASCADE, null=True, blank=True)
    work_order_templates = models.ManyToManyField(WorkOrderTemplate, through='TemplateTaskAssociation', related_name='task_templates')
    parent_template = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_templates')
    
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.template_name
        
    def generate_task(self, container, est_qty, product_identifier=None, product_instance=None, assignee=None):
        """Generate a Task from this template with specified quantity"""
        task = Task.objects.create(
            work_order=container if isinstance(container, WorkOrder) else None,
            est_worksheet=container if isinstance(container, EstWorksheet) else None,
            name=self.template_name,
            units=self.units,
            rate=self.rate,
            est_qty=est_qty,
            template=self,
            assignee=assignee
        )
        
        # Generate child tasks if this template has children
        for child_template in self.child_templates.filter(is_active=True):
            child_task = child_template.generate_task(
                container, 
                est_qty=est_qty,  # Pass the same quantity to child tasks
                product_identifier=product_identifier,
                product_instance=product_instance,
                assignee=assignee
            )
            child_task.parent_task = task
            child_task.save()
        
        return task
    
    def get_mapping_strategy(self):
        """Get the mapping strategy for this template"""
        return self.task_mapping.mapping_strategy if self.task_mapping else 'direct'
    
    def get_step_type(self):
        """Get the step type for this template"""
        return self.task_mapping.step_type if self.task_mapping else 'labor'
    
    def get_product_type(self):
        """Get the default product type for this template"""
        return self.task_mapping.default_product_type if self.task_mapping else ''


class EstimateLineItem(BaseLineItem):
    """Line item for estimates - inherits shared functionality from BaseLineItem."""

    estimate = models.ForeignKey(Estimate, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Estimate Line Item"
        verbose_name_plural = "Estimate Line Items"

    def get_parent_field_name(self):
        """Get the name of the parent field for this line item type."""
        return 'estimate'

    def __str__(self):
        return f"Estimate Line Item {self.pk} for {self.estimate.estimate_number}"


class ProductBundlingRule(models.Model):
    """Rules for how products are bundled into line items"""
    
    rule_id = models.AutoField(primary_key=True)
    rule_name = models.CharField(max_length=255)
    
    # What to bundle
    product_type = models.CharField(max_length=50)  # Match against TaskMapping.default_product_type
    work_order_template = models.ForeignKey(WorkOrderTemplate, on_delete=models.CASCADE, null=True, blank=True)
    
    # How to present as line item
    line_item_template = models.CharField(max_length=255)  # e.g., "Custom {product_type}"
    combine_instances = models.BooleanField(default=True)  # True: "4x Chair", False: separate lines
    
    # Pricing strategy
    PRICING_METHOD_CHOICES = [
        ('sum_components', 'Sum all component task prices'),
        ('template_base', 'Use WorkOrderTemplate base price'),
        ('custom_calculation', 'Custom calculation'),
    ]
    pricing_method = models.CharField(max_length=20, choices=PRICING_METHOD_CHOICES, default='sum_components')
    
    include_materials = models.BooleanField(default=True)
    include_labor = models.BooleanField(default=True)
    include_overhead = models.BooleanField(default=False)
    
    priority = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['priority', 'rule_name']
    
    def clean(self):
        """Validate ProductBundlingRule constraints"""
        from django.core.exceptions import ValidationError
        
        if self.pricing_method == 'template_base':
            if not self.work_order_template:
                raise ValidationError({
                    'work_order_template': 'template_base pricing requires a WorkOrderTemplate to be specified.'
                })
            
            if not self.work_order_template.base_price:
                raise ValidationError({
                    'work_order_template': f'The selected WorkOrderTemplate "{self.work_order_template.template_name}" must have a base_price set to use template_base pricing.'
                })
    
    def __str__(self):
        return f"Bundling Rule: {self.rule_name}"
