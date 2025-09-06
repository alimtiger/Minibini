from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from .models import Job, Estimate, Task, WorkOrder, WorkOrderTemplate, TaskTemplate
from .forms import WorkOrderTemplateForm, TaskTemplateForm
from apps.purchasing.models import PurchaseOrder

def job_list(request):
    jobs = Job.objects.all().order_by('-created_date')
    return render(request, 'jobs/job_list.html', {'jobs': jobs})

def job_detail(request, job_id):
    job = get_object_or_404(Job, job_id=job_id)
    estimates = Estimate.objects.filter(job=job).order_by('-created_date')
    purchase_orders = PurchaseOrder.objects.filter(job=job).order_by('-po_id')
    return render(request, 'jobs/job_detail.html', {'job': job, 'estimates': estimates, 'purchase_orders': purchase_orders})

def estimate_list(request):
    estimates = Estimate.objects.all().order_by('-estimate_id')
    return render(request, 'jobs/estimate_list.html', {'estimates': estimates})

def estimate_detail(request, estimate_id):
    estimate = get_object_or_404(Estimate, estimate_id=estimate_id)
    return render(request, 'jobs/estimate_detail.html', {'estimate': estimate})

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


def add_task_template(request, template_id):
    work_order_template = get_object_or_404(WorkOrderTemplate, template_id=template_id)
    
    if request.method == 'POST':
        form = TaskTemplateForm(request.POST)
        if form.is_valid():
            task_template = form.save(commit=False)
            task_template.work_order_template = work_order_template
            task_template.save()
            messages.success(request, f'Task Template "{task_template.template_name}" added successfully.')
            
            if 'add_another' in request.POST:
                return redirect('jobs:add_task_template', template_id=template_id)
            else:
                return redirect('jobs:work_order_template_detail', template_id=template_id)
    else:
        form = TaskTemplateForm()
    
    existing_tasks = TaskTemplate.objects.filter(work_order_template=work_order_template)
    
    return render(request, 'jobs/add_task_template.html', {
        'form': form,
        'work_order_template': work_order_template,
        'existing_tasks': existing_tasks
    })


def work_order_template_list(request):
    templates = WorkOrderTemplate.objects.filter(is_active=True).order_by('-created_date')
    return render(request, 'jobs/work_order_template_list.html', {'templates': templates})


def work_order_template_detail(request, template_id):
    template = get_object_or_404(WorkOrderTemplate, template_id=template_id)
    task_templates = TaskTemplate.objects.filter(work_order_template=template, is_active=True)
    return render(request, 'jobs/work_order_template_detail.html', {
        'template': template,
        'task_templates': task_templates
    })

