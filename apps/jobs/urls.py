from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('<int:job_id>/', views.job_detail, name='detail'),
    path('estimates/', views.estimate_list, name='estimate_list'),
    path('estimates/<int:estimate_id>/', views.estimate_detail, name='estimate_detail'),
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('workorders/', views.work_order_list, name='work_order_list'),
    path('workorders/<int:work_order_id>/', views.work_order_detail, name='work_order_detail'),
    path('templates/', views.work_order_template_list, name='work_order_template_list'),
    path('templates/add/', views.add_work_order_template, name='add_work_order_template'),
    path('templates/<int:template_id>/', views.work_order_template_detail, name='work_order_template_detail'),
    path('task-templates/', views.task_template_list, name='task_template_list'),
    path('task-templates/add/', views.add_task_template_standalone, name='add_task_template_standalone'),
    path('worksheets/', views.estworksheet_list, name='estworksheet_list'),
    path('worksheets/<int:worksheet_id>/', views.estworksheet_detail, name='estworksheet_detail'),
    path('worksheets/<int:worksheet_id>/generate-estimate/', views.estworksheet_generate_estimate, name='estworksheet_generate_estimate'),
    path('task-mappings/', views.task_mapping_list, name='task_mapping_list'),
]