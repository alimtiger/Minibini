from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from .models import Job, Estimate, EstimateLineItem, Task, WorkOrder, WorkOrderTemplate, TaskTemplate, EstWorksheet, TaskMapping
from .forms import WorkOrderTemplateForm, TaskTemplateForm
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

def estimate_list(request):
    estimates = Estimate.objects.all().order_by('-estimate_id')
    return render(request, 'jobs/estimate_list.html', {'estimates': estimates})

def estimate_detail(request, estimate_id):
    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)
    line_items = EstimateLineItem.objects.filter(estimate=estimate).order_by('line_item_id')
    # Calculate total amount
    total_amount = sum(item.total_amount for item in line_items)
    # Check for associated worksheet
    worksheet = EstWorksheet.objects.filter(estimate=estimate).first()
    return render(request, 'jobs/estimate_detail.html', {
        'estimate': estimate,
        'line_items': line_items,
        'total_amount': total_amount,
        'worksheet': worksheet
    })

def task_list(request):
    tasks = Task.objects.all().order_by('-task_id')
    return render(request, 'jobs/task_list.html', {'tasks': tasks})

def task_detail(request, task_id):
    task = get_object_or_404(Task, task_id=task_id)
    return render(request, 'jobs/task_detail.html', {'task': task})

def work_order_list(request):
    work_orders = WorkOrder.objects.all().order_by('-work_order_id')
    return render(request, 'jobs/work_order_list.html', {'work_orders': work_orders})

def work_order_detail(request, work_order_id):
    work_order = get_object_or_404(WorkOrder, work_order_id=work_order_id)
    tasks = Task.objects.filter(work_order=work_order).order_by('task_id')
    return render(request, 'jobs/work_order_detail.html', {'work_order': work_order, 'tasks': tasks})


def add_work_order_template(request):
    if request.method == 'POST':
        form = WorkOrderTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'Work Order Template "{template.template_name}" created successfully.')
            if 'add_task' in request.POST:
                return redirect('jobs:add_task_template', template_id=template.template_id)
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
            association, created = TemplateTaskAssociation.objects.get_or_create(
                work_order_template=template,
                task_template=task_template,
                defaults={'est_qty': est_qty}
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
    
    # Calculate worksheet totals
    total_cost = sum(task.rate * task.est_qty for task in tasks if task.rate and task.est_qty)
    
    return render(request, 'jobs/estworksheet_detail.html', {
        'worksheet': worksheet,
        'tasks': tasks,
        'total_cost': total_cost
    })


def estworksheet_generate_estimate(request, worksheet_id):
    """Generate an estimate from a worksheet using EstimateGenerationService"""
    worksheet = get_object_or_404(EstWorksheet, est_worksheet_id=worksheet_id)
    
    if request.method == 'POST':
        try:
            from .services import EstimateGenerationService
            service = EstimateGenerationService()
            estimate = service.generate_estimate_from_worksheet(worksheet)
            
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

