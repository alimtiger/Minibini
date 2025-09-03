from django.shortcuts import render, get_object_or_404
from .models import Job, Estimate, Task, WorkOrder
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

