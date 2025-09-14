"""
Service classes for handling complex creation workflows between Jobs, WorkOrders, Estimates, and Tasks.
"""

from django.core.exceptions import ValidationError
from .models import Job, WorkOrder, Estimate, Task, WorkOrderTemplate, TaskTemplate
from apps.invoicing.models import PriceListItem


class WorkOrderService:
    """Service class for WorkOrder creation workflows."""
    
    @staticmethod
    def create_from_estimate(estimate):
        """
        Create WorkOrder from Estimate.
        Only Open and Accepted Estimates can create WorkOrders.
        Created WorkOrder starts in 'incomplete' status.
        """
        if estimate.status not in ['open', 'accepted']:
            raise ValidationError(
                f"Only Open and Accepted estimates can create WorkOrders. "
                f"Estimate {estimate.estimate_number} is {estimate.status}."
            )
        
        work_order = WorkOrder.objects.create(
            job=estimate.job,
            status='incomplete'
        )
        
        # Convert LineItems to Tasks via TaskMapping (placeholder for now)
        for line_item in estimate.estimatelineitem_set.all():
            TaskService.create_from_line_item(line_item, work_order)
            
        return work_order
    
    @staticmethod
    def create_from_template(template, job):
        """
        Create WorkOrder from WorkOrderTemplate.
        Created WorkOrder starts in 'draft' status.
        """
        if not template.is_active:
            raise ValidationError(f"Template {template.template_name} is not active.")
            
        work_order = WorkOrder.objects.create(
            job=job,
            template=template,
            status='draft'
        )
        
        # Generate Tasks from TaskTemplates
        for task_template in template.tasktemplate_set.filter(is_active=True):
            TaskService.create_from_template(task_template, work_order)
            
        return work_order
    
    @staticmethod
    def create_direct(job, **kwargs):
        """Create WorkOrder directly. Starts in 'draft' status."""
        return WorkOrder.objects.create(
            job=job,
            status='draft',
            **kwargs
        )


class EstimateService:
    """Service class for Estimate creation workflows."""
    
    @staticmethod
    def create_from_work_order(work_order):
        """
        Create Estimate from WorkOrder.
        Only Draft WorkOrders can create Estimates.
        Created Estimate starts in 'draft' status.
        """
        if work_order.status != 'draft':
            raise ValidationError(
                f"Only Draft WorkOrders can create Estimates. "
                f"WorkOrder {work_order.pk} is {work_order.status}."
            )
        
        estimate = Estimate.objects.create(
            job=work_order.job,
            estimate_number=f"EST-{work_order.job.job_number}-{work_order.pk}",
            status='draft'
        )
        
        # Convert Tasks to LineItems via TaskMapping (placeholder for now)
        from .models import EstimateLineItem
        for task in work_order.task_set.all():
            TaskService.create_line_item_from_task(task, estimate)
            
        return estimate
    
    @staticmethod
    def create_direct(job, estimate_number, **kwargs):
        """Create Estimate directly. Starts in 'draft' status."""
        return Estimate.objects.create(
            job=job,
            estimate_number=estimate_number,
            status='draft',
            **kwargs
        )


class TaskService:
    """Service class for Task creation workflows."""
    
    @staticmethod
    def create_from_line_item(line_item, work_order):
        """
        Create Task from LineItem.
        Uses TaskMapping for translation (placeholder for now).
        """
        # Placeholder: TaskMapping translation will be implemented later
        task = Task.objects.create(
            work_order=work_order,
            name=f"Task from {line_item.description or 'LineItem'}",
        )
        return task
    
    @staticmethod
    def create_from_template(template, work_order, assignee=None):
        """
        Create Task from TaskTemplate.
        Direct creation - no TaskMapping involved.
        """
        if not template.is_active:
            raise ValidationError(f"Template {template.template_name} is not active.")
            
        task = Task.objects.create(
            work_order=work_order,
            template=template,
            name=template.template_name,
            assignee=assignee
        )
        return task
    
    @staticmethod
    def create_direct(work_order, name, **kwargs):
        """Create Task directly."""
        return Task.objects.create(
            work_order=work_order,
            name=name,
            **kwargs
        )
    
    @staticmethod
    def create_line_item_from_task(task, estimate):
        """
        Create LineItem from Task.
        Uses TaskMapping for translation (placeholder for now).
        """
        # Placeholder: TaskMapping translation will be implemented later
        from .models import EstimateLineItem
        line_item = EstimateLineItem.objects.create(
            estimate=estimate,
            description=f"LineItem from {task.name}",
            qty=1,
            units="each",
            price_currency=0
        )
        return line_item