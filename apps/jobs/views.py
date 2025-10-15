from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django import forms
from django.utils import timezone
from django.db import models
from .models import Job, Estimate, EstimateLineItem, Task, WorkOrder, WorkOrderTemplate, TaskTemplate, EstWorksheet, TaskMapping, TaskInstanceMapping
from .forms import (
    JobCreateForm, JobEditForm, WorkOrderTemplateForm, TaskTemplateForm, EstWorksheetForm,
    TaskForm, TaskFromTemplateForm,
    ManualLineItemForm, PriceListLineItemForm, EstimateStatusForm, EstimateForm, WorkOrderStatusForm
)
from apps.purchasing.models import PurchaseOrder
from apps.invoicing.models import Invoice

def job_list(request):
    jobs = Job.objects.all().order_by('-created_date')
    return render(request, 'jobs/job_list.html', {'jobs': jobs})

def job_detail(request, job_id):
    job = get_object_or_404(Job, job_id=job_id)
    estimates = Estimate.objects.filter(job=job).order_by('-created_date')
    work_orders = WorkOrder.objects.filter(job=job).order_by('-work_order_id')
    worksheets = EstWorksheet.objects.filter(job=job).order_by('-created_date')
    purchase_orders = PurchaseOrder.objects.filter(job=job).order_by('-po_id')
    invoices = Invoice.objects.filter(job=job).order_by('-invoice_id')
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'estimates': estimates,
        'work_orders': work_orders,
        'worksheets': worksheets,
        'purchase_orders': purchase_orders,
        'invoices': invoices
    })


def job_create(request):
    """Create a new Job"""
    initial_contact_id = request.GET.get('contact_id')
    initial_contact = None

    if initial_contact_id:
        try:
            from apps.contacts.models import Contact
            initial_contact = Contact.objects.get(contact_id=initial_contact_id)
        except Contact.DoesNotExist:
            pass

    if request.method == 'POST':
        form = JobCreateForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            # Job starts in 'draft' status by default (defined in model)
            job.save()
            messages.success(request, f'Job {job.job_number} created successfully.')
            return redirect('jobs:detail', job_id=job.job_id)
    else:
        form = JobCreateForm(initial_contact=initial_contact)

    return render(request, 'jobs/job_create.html', {
        'form': form,
        'initial_contact': initial_contact
    })


def job_edit(request, job_id):
    """Edit an existing Job with state-based field restrictions"""
    job = get_object_or_404(Job, job_id=job_id)

    if request.method == 'POST':
        form = JobEditForm(request.POST, instance=job)
        if form.is_valid():
            job = form.save()
            messages.success(request, f'Job {job.job_number} updated successfully.')
            return redirect('jobs:detail', job_id=job.job_id)
    else:
        form = JobEditForm(instance=job)

    return render(request, 'jobs/job_edit.html', {
        'form': form,
        'job': job
    })


def estimate_list(request):
    estimates = Estimate.objects.all().order_by('-estimate_id')
    return render(request, 'jobs/estimate_list.html', {'estimates': estimates})

def estimate_detail(request, estimate_id):
    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)

    # Handle status update POST request
    if request.method == 'POST' and 'update_status' in request.POST:
        # Check if status transitions are allowed
        if EstimateStatusForm.has_valid_transitions(estimate.status):
            form = EstimateStatusForm(request.POST, current_status=estimate.status)
            if form.is_valid():
                new_status = form.cleaned_data['status']
                if new_status != estimate.status:
                    try:
                        estimate.status = new_status
                        estimate.save()
                        messages.success(request, f'Estimate status updated to {new_status.title()}')
                    except Exception as e:
                        messages.error(request, f'Error updating status: {str(e)}')
                return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)
        else:
            messages.error(request, f'Cannot update status from {estimate.get_status_display()} (terminal state).')
            return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)

    # Get line items and calculate total
    line_items = EstimateLineItem.objects.filter(estimate=estimate).order_by('line_item_id')
    total_amount = sum(item.total_amount for item in line_items)

    # Check for associated worksheet
    worksheet = EstWorksheet.objects.filter(estimate=estimate).first()

    # Create status form for display only if there are valid transitions
    status_form = None
    if EstimateStatusForm.has_valid_transitions(estimate.status):
        status_form = EstimateStatusForm(current_status=estimate.status)

    return render(request, 'jobs/estimate_detail.html', {
        'estimate': estimate,
        'line_items': line_items,
        'total_amount': total_amount,
        'worksheet': worksheet,
        'status_form': status_form
    })

def task_list(request):
    # Only show incomplete tasks with WorkOrders (not EstWorksheets)
    tasks = Task.objects.filter(
        work_order__isnull=False,
        est_worksheet__isnull=True
    ).exclude(
        work_order__status='complete'
    ).select_related('work_order', 'work_order__job', 'assignee').order_by('-task_id')
    return render(request, 'jobs/task_list.html', {'tasks': tasks})

def task_detail(request, task_id):
    task = get_object_or_404(Task, task_id=task_id)
    return render(request, 'jobs/task_detail.html', {'task': task})

def work_order_list(request):
    work_orders = WorkOrder.objects.all().order_by('-work_order_id')
    return render(request, 'jobs/work_order_list.html', {'work_orders': work_orders})

def work_order_detail(request, work_order_id):
    work_order = get_object_or_404(WorkOrder, work_order_id=work_order_id)

    # Handle status update POST request
    if request.method == 'POST' and 'update_status' in request.POST:
        if work_order.status != 'complete':
            form = WorkOrderStatusForm(request.POST, current_status=work_order.status)
            if form.is_valid():
                new_status = form.cleaned_data['status']
                if new_status != work_order.status:
                    work_order.status = new_status
                    work_order.save()
                    messages.success(request, f'Work Order status updated to {new_status.title()}')
            return redirect('jobs:work_order_detail', work_order_id=work_order.work_order_id)
        else:
            messages.error(request, 'Cannot update the status of a completed work order.')
            return redirect('jobs:work_order_detail', work_order_id=work_order.work_order_id)

    # Get all tasks for this work order
    all_tasks = Task.objects.filter(work_order=work_order).order_by('task_id')

    # Build hierarchical task structure
    def build_task_tree(tasks):
        """Build a hierarchical task structure with level indicators."""
        task_dict = {task.task_id: task for task in tasks}
        root_tasks = []

        # Find root tasks (no parent)
        for task in tasks:
            if not task.parent_task:
                root_tasks.append(task)

        # Recursive function to get task with its children and level
        def get_task_with_children(task, level=0):
            result = {'task': task, 'level': level}
            children = []
            for potential_child in tasks:
                if potential_child.parent_task_id == task.task_id:
                    children.append(get_task_with_children(potential_child, level + 1))
            result['children'] = children
            return result

        # Build the tree
        tree = []
        for root_task in root_tasks:
            tree.append(get_task_with_children(root_task))

        # Flatten the tree for template display
        def flatten_tree(tree_nodes):
            flat_list = []
            for node in tree_nodes:
                flat_list.append({'task': node['task'], 'level': node['level']})
                if node['children']:
                    flat_list.extend(flatten_tree(node['children']))
            return flat_list

        return flatten_tree(tree)

    tasks_with_levels = build_task_tree(all_tasks)

    # Create status form for display (unless completed)
    status_form = WorkOrderStatusForm(current_status=work_order.status) if work_order.status != 'complete' else None

    return render(request, 'jobs/work_order_detail.html', {
        'work_order': work_order,
        'tasks': tasks_with_levels,
        'status_form': status_form
    })


def work_order_create_from_estimate(request, estimate_id):
    """Create a WorkOrder from an accepted Estimate"""
    from django.db import transaction

    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)

    # Only allow creation from accepted estimates
    if estimate.status != 'accepted':
        messages.error(request, 'Work Orders can only be created from accepted estimates.')
        return redirect('jobs:estimate_detail', estimate_id=estimate_id)

    if request.method == 'POST':
        with transaction.atomic():
            # Create the WorkOrder
            work_order = WorkOrder.objects.create(
                job=estimate.job,
                status='draft',
                template=None
            )

            # Generate tasks from all EstimateLineItems
            from .services import LineItemTaskService
            total_tasks = 0
            line_items = estimate.estimatelineitem_set.all().order_by('line_number', 'pk')

            for line_item in line_items:
                generated_tasks = LineItemTaskService.generate_tasks_for_work_order(line_item, work_order)
                total_tasks += len(generated_tasks)

            # If we have worksheet-based tasks, try to set template from worksheet
            worksheet = EstWorksheet.objects.filter(estimate=estimate).first()
            if worksheet:
                work_order.template = worksheet.template
                work_order.save()

            messages.success(request, f'Work Order {work_order.work_order_id} created successfully from Estimate {estimate.estimate_number}.')
            return redirect('jobs:work_order_detail', work_order_id=work_order.work_order_id)

    # GET request - show confirmation page
    worksheet = EstWorksheet.objects.filter(estimate=estimate).first()
    line_items = estimate.estimatelineitem_set.all().order_by('line_number', 'pk')

    # Categorize line items by source
    worksheet_items = []
    catalog_items = []
    manual_items = []

    for line_item in line_items:
        if line_item.task:
            worksheet_items.append(line_item)
        elif line_item.price_list_item:
            catalog_items.append(line_item)
        else:
            manual_items.append(line_item)

    return render(request, 'jobs/work_order_create_confirm.html', {
        'estimate': estimate,
        'worksheet': worksheet,
        'line_items': line_items,
        'worksheet_items': worksheet_items,
        'catalog_items': catalog_items,
        'manual_items': manual_items,
        'total_line_items': line_items.count()
    })


def add_work_order_template(request):
    if request.method == 'POST':
        form = WorkOrderTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'Work Order Template "{template.template_name}" created successfully.')
            return redirect('jobs:work_order_template_detail', template_id=template.template_id)
    else:
        form = WorkOrderTemplateForm()

    return render(request, 'jobs/add_work_order_template.html', {'form': form})



def work_order_template_list(request):
    templates = WorkOrderTemplate.objects.filter(is_active=True).order_by('-created_date')
    return render(request, 'jobs/work_order_template_list.html', {'templates': templates})


def work_order_template_detail(request, template_id):
    template = get_object_or_404(WorkOrderTemplate, template_id=template_id)
    
    # Handle TaskTemplate association
    if request.method == 'POST' and 'associate_task' in request.POST:
        task_template_id = request.POST.get('task_template_id')
        est_qty = request.POST.get('est_qty', '1.00')
        if task_template_id:
            from .models import TemplateTaskAssociation
            task_template = get_object_or_404(TaskTemplate, template_id=task_template_id)

            # Get the next sort_order value
            max_sort_order = TemplateTaskAssociation.objects.filter(
                work_order_template=template
            ).aggregate(models.Max('sort_order'))['sort_order__max']
            next_sort_order = (max_sort_order or 0) + 1

            association, created = TemplateTaskAssociation.objects.get_or_create(
                work_order_template=template,
                task_template=task_template,
                defaults={'est_qty': est_qty, 'sort_order': next_sort_order}
            )
            if created:
                messages.success(request, f'Task Template "{task_template.template_name}" associated with quantity {est_qty}.')
            else:
                messages.warning(request, f'Task Template "{task_template.template_name}" is already associated.')
        return redirect('jobs:work_order_template_detail', template_id=template_id)
    
    # Handle TaskTemplate disassociation
    if request.method == 'POST' and 'remove_task' in request.POST:
        task_template_id = request.POST.get('task_template_id')
        if task_template_id:
            from .models import TemplateTaskAssociation
            task_template = get_object_or_404(TaskTemplate, template_id=task_template_id)
            TemplateTaskAssociation.objects.filter(
                work_order_template=template,
                task_template=task_template
            ).delete()
            messages.success(request, f'Task Template "{task_template.template_name}" removed successfully.')
        return redirect('jobs:work_order_template_detail', template_id=template_id)
    
    # Get task template associations
    from .models import TemplateTaskAssociation
    associations = TemplateTaskAssociation.objects.filter(
        work_order_template=template,
        task_template__is_active=True
    ).select_related('task_template').order_by('sort_order', 'task_template__template_name')
    
    # Get available task templates (not yet associated)
    associated_task_ids = associations.values_list('task_template_id', flat=True)
    available_templates = TaskTemplate.objects.filter(is_active=True).exclude(template_id__in=associated_task_ids)
    
    return render(request, 'jobs/work_order_template_detail.html', {
        'template': template,
        'associations': associations,
        'available_templates': available_templates
    })


def estworksheet_list(request):
    """List all EstWorksheets"""
    worksheets = EstWorksheet.objects.select_related('job', 'estimate').order_by('-created_date')
    return render(request, 'jobs/estworksheet_list.html', {'worksheets': worksheets})


def estworksheet_detail(request, worksheet_id):
    """Show details of a specific EstWorksheet with its tasks"""
    worksheet = get_object_or_404(EstWorksheet, est_worksheet_id=worksheet_id)
    tasks = Task.objects.filter(est_worksheet=worksheet).select_related(
        'template', 'template__task_mapping'
    ).prefetch_related('taskinstancemapping')

    # Add calculated total for each task
    for task in tasks:
        task.calculated_total = (task.rate * task.est_qty) if task.rate and task.est_qty else 0

    # Calculate worksheet totals
    total_cost = sum(task.calculated_total for task in tasks)

    return render(request, 'jobs/estworksheet_detail.html', {
        'worksheet': worksheet,
        'tasks': tasks,
        'total_cost': total_cost
    })


def estworksheet_generate_estimate(request, worksheet_id):
    """Generate an estimate from a worksheet using EstimateGenerationService"""
    worksheet = get_object_or_404(EstWorksheet, est_worksheet_id=worksheet_id)

    # Prevent generating estimates from non-draft worksheets
    if worksheet.status != 'draft':
        messages.error(request, f'Cannot generate estimate from a {worksheet.get_status_display().lower()} worksheet.')
        return redirect('jobs:estworksheet_detail', worksheet_id=worksheet_id)

    if request.method == 'POST':
        try:
            from .services import EstimateGenerationService
            service = EstimateGenerationService()
            estimate = service.generate_estimate_from_worksheet(worksheet)

            # Mark worksheet as final after generating estimate
            worksheet.status = 'final'
            worksheet.save()

            messages.success(request, f'Estimate {estimate.estimate_number} generated successfully!')
            return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)
            
        except Exception as e:
            messages.error(request, f'Error generating estimate: {str(e)}')
            return redirect('jobs:estworksheet_detail', worksheet_id=worksheet_id)
    
    # Show confirmation page
    tasks = Task.objects.filter(est_worksheet=worksheet).select_related(
        'template', 'template__task_mapping'
    )
    total_cost = sum(task.rate * task.est_qty for task in tasks if task.rate and task.est_qty)
    
    return render(request, 'jobs/estworksheet_generate_estimate.html', {
        'worksheet': worksheet,
        'tasks': tasks,
        'total_cost': total_cost
    })


def task_mapping_list(request):
    """List all TaskMappings"""
    mappings = TaskMapping.objects.all().order_by('mapping_strategy', 'step_type', 'task_type_id')
    return render(request, 'jobs/task_mapping_list.html', {'mappings': mappings})


def estimate_mark_open(request, estimate_id):
    """Mark an estimate as Open and update associated worksheet to Final"""
    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)

    if request.method == 'POST':
        if estimate.status == 'draft':
            # Mark estimate as open
            estimate.status = 'open'
            estimate.save()

            # Update associated worksheet to final if exists
            worksheet = EstWorksheet.objects.filter(estimate=estimate).first()
            if worksheet and worksheet.status == 'draft':
                worksheet.status = 'final'
                worksheet.save()

            messages.success(request, f'Estimate {estimate.estimate_number} marked as Open')
        else:
            messages.warning(request, 'Only Draft estimates can be marked as Open')

    return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)


def estworksheet_revise(request, worksheet_id):
    """Create a new revision of a worksheet"""
    parent_worksheet = get_object_or_404(EstWorksheet, est_worksheet_id=worksheet_id)

    if request.method == 'POST':
        if parent_worksheet.status != 'draft':
            # Create new draft worksheet
            new_worksheet = EstWorksheet.objects.create(
                job=parent_worksheet.job,
                parent=parent_worksheet,
                status='draft',
                version=parent_worksheet.version + 1
            )

            # Copy tasks from parent to new worksheet
            parent_tasks = Task.objects.filter(est_worksheet=parent_worksheet)
            for task in parent_tasks:
                new_task = Task.objects.create(
                    name=task.name,
                    template=task.template,
                    est_worksheet=new_worksheet,
                    est_qty=task.est_qty,
                    units=task.units,
                    rate=task.rate
                )

                # Copy instance mapping if exists
                try:
                    instance_mapping = TaskInstanceMapping.objects.get(task=task)
                    TaskInstanceMapping.objects.create(
                        task=new_task,
                        product_identifier=instance_mapping.product_identifier,
                        product_instance=instance_mapping.product_instance
                    )
                except TaskInstanceMapping.DoesNotExist:
                    pass

            # Mark parent as superseded and increment version
            parent_worksheet.status = 'superseded'
            parent_worksheet.save()

            messages.success(request, f'New worksheet revision created (v{new_worksheet.version})')
            return redirect('jobs:estworksheet_detail', worksheet_id=new_worksheet.est_worksheet_id)
        else:
            messages.warning(request, 'Cannot revise a Draft worksheet')

    return redirect('jobs:estworksheet_detail', worksheet_id=worksheet_id)


def task_template_list(request):
    """List all TaskTemplates with all fields"""
    templates = TaskTemplate.objects.filter(is_active=True).select_related('task_mapping').prefetch_related('work_order_templates').order_by('template_name')
    return render(request, 'jobs/task_template_list.html', {'templates': templates})


def add_task_template_standalone(request):
    """Create a new TaskTemplate independently"""
    if request.method == 'POST':
        form = TaskTemplateForm(request.POST)
        if form.is_valid():
            task_template = form.save()
            messages.success(request, f'Task Template "{task_template.template_name}" created successfully.')
            return redirect('jobs:task_template_list')
    else:
        form = TaskTemplateForm()

    return render(request, 'jobs/add_task_template_standalone.html', {'form': form})


def estworksheet_create(request):
    """Create a new EstWorksheet manually"""
    if request.method == 'POST':
        form = EstWorksheetForm(request.POST)
        if form.is_valid():
            worksheet = form.save()
            messages.success(request, f'Worksheet created successfully')
            return redirect('jobs:estworksheet_detail', worksheet_id=worksheet.est_worksheet_id)
    else:
        form = EstWorksheetForm()

    return render(request, 'jobs/estworksheet_create.html', {'form': form})


def estworksheet_create_for_job(request, job_id):
    """Create a new EstWorksheet for a specific Job, optionally from a template"""
    job = get_object_or_404(Job, job_id=job_id)

    if request.method == 'POST':
        form = EstWorksheetForm(request.POST, initial={'job': job})
        if form.is_valid():
            worksheet = form.save(commit=False)
            worksheet.job = job  # Ensure job is set
            worksheet.save()

            # If a template was selected, create tasks from it
            template = form.cleaned_data.get('template')
            if template:
                # Create tasks from template's task templates
                from .models import TemplateTaskAssociation
                associations = TemplateTaskAssociation.objects.filter(
                    work_order_template=template,
                    task_template__is_active=True
                ).select_related('task_template').order_by('sort_order', 'task_template__template_name')

                for association in associations:
                    Task.objects.create(
                        name=association.task_template.template_name,
                        template=association.task_template,
                        est_worksheet=worksheet,
                        est_qty=association.est_qty,  # Use the association's quantity
                        units=association.task_template.units,
                        rate=association.task_template.rate
                    )

                messages.success(request, f'Worksheet created from template "{template.template_name}" for Job {job.job_number}')
            else:
                messages.success(request, f'Worksheet created successfully for Job {job.job_number}')

            return redirect('jobs:estworksheet_detail', worksheet_id=worksheet.est_worksheet_id)
    else:
        form = EstWorksheetForm(initial={'job': job})
        # Hide the job field since it's already set
        form.fields['job'].widget = forms.HiddenInput()

    return render(request, 'jobs/estworksheet_create_for_job.html', {
        'form': form,
        'job': job
    })


# Removed estworksheet_create_from_template - functionality merged into estworksheet_create_for_job


def task_add_from_template(request, worksheet_id):
    """Add Task to EstWorksheet from TaskTemplate"""
    worksheet = get_object_or_404(EstWorksheet, est_worksheet_id=worksheet_id)

    # Prevent adding tasks to non-draft worksheets
    if worksheet.status != 'draft':
        messages.error(request, f'Cannot add tasks to a {worksheet.get_status_display().lower()} worksheet.')
        return redirect('jobs:estworksheet_detail', worksheet_id=worksheet_id)

    if request.method == 'POST':
        form = TaskFromTemplateForm(request.POST)
        if form.is_valid():
            template = form.cleaned_data['template']
            est_qty = form.cleaned_data['est_qty']

            task = Task.objects.create(
                name=template.template_name,
                template=template,
                est_worksheet=worksheet,
                est_qty=est_qty,
                units=template.units,
                rate=template.rate
            )

            messages.success(request, f'Task "{task.name}" added from template')
            return redirect('jobs:estworksheet_detail', worksheet_id=worksheet.est_worksheet_id)
    else:
        form = TaskFromTemplateForm()

    return render(request, 'jobs/task_add_from_template.html', {
        'form': form,
        'worksheet': worksheet
    })


def task_add_manual(request, worksheet_id):
    """Add Task to EstWorksheet manually"""
    worksheet = get_object_or_404(EstWorksheet, est_worksheet_id=worksheet_id)

    # Prevent adding tasks to non-draft worksheets
    if worksheet.status != 'draft':
        messages.error(request, f'Cannot add tasks to a {worksheet.get_status_display().lower()} worksheet.')
        return redirect('jobs:estworksheet_detail', worksheet_id=worksheet_id)

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.est_worksheet = worksheet
            task.save()

            messages.success(request, f'Task "{task.name}" added manually')
            return redirect('jobs:estworksheet_detail', worksheet_id=worksheet.est_worksheet_id)
    else:
        form = TaskForm(initial={'est_worksheet': worksheet})
        # Hide the worksheet field since it's already set
        form.fields['est_worksheet'].widget = forms.HiddenInput()

    return render(request, 'jobs/task_add_manual.html', {
        'form': form,
        'worksheet': worksheet
    })


def estimate_delete_line_item(request, estimate_id, line_item_id):
    """Delete a line item from an estimate and renumber remaining items"""
    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)
    line_item = get_object_or_404(EstimateLineItem, line_item_id=line_item_id, estimate=estimate)

    # Prevent modifications to superseded estimates
    if estimate.status == 'superseded':
        messages.error(request, 'Cannot delete line items from a superseded estimate.')
        return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)

    if request.method == 'POST':
        # Store the line number before deleting
        deleted_line_number = line_item.line_number

        # Delete the line item
        line_item.delete()

        # Renumber remaining line items
        remaining_items = EstimateLineItem.objects.filter(
            estimate=estimate
        ).order_by('line_number', 'line_item_id')

        # Reassign line numbers sequentially
        for index, item in enumerate(remaining_items, start=1):
            if item.line_number != index:
                item.line_number = index
                item.save()

        messages.success(request, f'Line item deleted and remaining items renumbered.')
        return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)

    # GET request - show confirmation (optional, can skip for simple delete)
    return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)


def estimate_add_line_item(request, estimate_id):
    """Add line item to Estimate - either manually or from Price List"""
    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)

    # Prevent modifications to superseded estimates
    if estimate.status == 'superseded':
        messages.error(request, 'Cannot add line items to a superseded estimate.')
        return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)

    if request.method == 'POST':
        # Determine which form was submitted
        if 'manual_submit' in request.POST:
            # Manual line item form submitted
            manual_form = ManualLineItemForm(request.POST)
            if manual_form.is_valid():
                line_item = manual_form.save(commit=False)
                line_item.estimate = estimate
                line_item.save()

                messages.success(request, f'Line item "{line_item.description}" added')
                return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)
            else:
                # Manual form has errors, create empty price list form
                pricelist_form = PriceListLineItemForm()

        elif 'pricelist_submit' in request.POST:
            # Price list line item form submitted
            pricelist_form = PriceListLineItemForm(request.POST)
            if pricelist_form.is_valid():
                price_list_item = pricelist_form.cleaned_data['price_list_item']
                qty = pricelist_form.cleaned_data['qty']

                # Create line item from price list item
                line_item = EstimateLineItem.objects.create(
                    estimate=estimate,
                    price_list_item=price_list_item,
                    description=price_list_item.description,
                    qty=qty,
                    units=price_list_item.units,
                    price_currency=price_list_item.selling_price
                )

                messages.success(request, f'Line item "{line_item.description}" added from price list')
                return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)
            else:
                # Price list form has errors, create empty manual form
                manual_form = ManualLineItemForm()
        else:
            # Neither form submitted (shouldn't happen)
            manual_form = ManualLineItemForm()
            pricelist_form = PriceListLineItemForm()
    else:
        # GET request - create both empty forms
        manual_form = ManualLineItemForm()
        pricelist_form = PriceListLineItemForm()

    return render(request, 'jobs/estimate_add_line_item.html', {
        'manual_form': manual_form,
        'pricelist_form': pricelist_form,
        'estimate': estimate
    })


def estimate_update_status(request, estimate_id):
    """Update Estimate status"""
    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)

    # Prevent modifications to superseded estimates
    if estimate.status == 'superseded':
        messages.error(request, 'Cannot update the status of a superseded estimate.')
        return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)

    if request.method == 'POST':
        form = EstimateStatusForm(request.POST, current_status=estimate.status)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            if new_status != estimate.status:
                estimate.status = new_status
                estimate.save()
                messages.success(request, f'Estimate status updated to {new_status.title()}')
            return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)
    else:
        form = EstimateStatusForm(current_status=estimate.status)

    return render(request, 'jobs/estimate_update_status.html', {
        'form': form,
        'estimate': estimate
    })


def estimate_create_for_job(request, job_id):
    """Create a new Estimate for a specific Job - creates directly with defaults"""
    from apps.core.services import NumberGenerationService

    job = get_object_or_404(Job, job_id=job_id)

    # Check if an estimate already exists for this job
    existing_estimate = Estimate.objects.filter(job=job).exclude(status='superseded').first()
    if existing_estimate:
        if existing_estimate.status == 'draft':
            # Redirect to existing draft estimate for editing
            messages.info(request, f'A draft estimate already exists for this job. You can edit it here.')
            return redirect('jobs:estimate_detail', estimate_id=existing_estimate.estimate_id)
        else:
            # For non-draft estimates, user must use revise functionality
            messages.error(request, f'An estimate already exists for this job. Use the Revise option to create a new version.')
            return redirect('jobs:estimate_detail', estimate_id=existing_estimate.estimate_id)

    # Create estimate directly with defaults
    estimate = Estimate.objects.create(
        job=job,
        estimate_number=NumberGenerationService.generate_next_number('estimate'),
        version=1,
        status='draft'
    )

    messages.success(request, f'Estimate {estimate.estimate_number} (v{estimate.version}) created successfully')
    return redirect('jobs:estimate_detail', estimate_id=estimate.estimate_id)


def estimate_revise(request, estimate_id):
    """Create a new revision of an estimate"""
    parent_estimate = get_object_or_404(Estimate, estimate_id=estimate_id)

    if request.method == 'POST':
        if parent_estimate.status != 'draft':
            # Create new draft estimate
            new_estimate = Estimate.objects.create(
                job=parent_estimate.job,
                estimate_number=parent_estimate.estimate_number,
                version=parent_estimate.version + 1,
                status='draft',
                parent=parent_estimate
            )

            # Copy line items from parent to new estimate
            parent_line_items = EstimateLineItem.objects.filter(estimate=parent_estimate)
            for line_item in parent_line_items:
                EstimateLineItem.objects.create(
                    estimate=new_estimate,
                    task=line_item.task,
                    price_list_item=line_item.price_list_item,
                    qty=line_item.qty,
                    units=line_item.units,
                    description=line_item.description,
                    price_currency=line_item.price_currency
                )

            # Mark parent as superseded
            parent_estimate.status = 'superseded'
            parent_estimate.superseded_date = timezone.now()
            parent_estimate.save()

            messages.success(request, f'Created new revision of estimate {new_estimate.estimate_number} (v{new_estimate.version})')
            return redirect('jobs:estimate_detail', estimate_id=new_estimate.estimate_id)
        else:
            messages.info(request, 'Cannot revise a draft estimate. Please edit it directly.')
            return redirect('jobs:estimate_detail', estimate_id=parent_estimate.estimate_id)

    return render(request, 'jobs/estimate_revise_confirm.html', {
        'estimate': parent_estimate
    })

