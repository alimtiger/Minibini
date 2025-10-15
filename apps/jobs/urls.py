from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.job_list, name='list'),
    path('create/', views.job_create, name='create'),
    path('<int:job_id>/', views.job_detail, name='detail'),
    path('<int:job_id>/edit/', views.job_edit, name='edit'),
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
    path('worksheets/<int:worksheet_id>/revise/', views.estworksheet_revise, name='estworksheet_revise'),
    path('estimates/<int:estimate_id>/mark-open/', views.estimate_mark_open, name='estimate_mark_open'),
    path('estimates/<int:estimate_id>/update-status/', views.estimate_update_status, name='estimate_update_status'),
    path('estimates/<int:estimate_id>/add-line-item/', views.estimate_add_line_item, name='estimate_add_line_item'),
    path('estimates/<int:estimate_id>/delete-line-item/<int:line_item_id>/', views.estimate_delete_line_item, name='estimate_delete_line_item'),
    path('estimates/<int:estimate_id>/revise/', views.estimate_revise, name='estimate_revise'),
    path('estimates/<int:estimate_id>/create-work-order/', views.work_order_create_from_estimate, name='work_order_create_from_estimate'),
    path('worksheets/create/', views.estworksheet_create, name='estworksheet_create'),
    path('<int:job_id>/create-worksheet/', views.estworksheet_create_for_job, name='estworksheet_create_for_job'),
    path('worksheets/<int:worksheet_id>/add-task-from-template/', views.task_add_from_template, name='task_add_from_template'),
    path('worksheets/<int:worksheet_id>/add-task-manual/', views.task_add_manual, name='task_add_manual'),
    path('task-mappings/', views.task_mapping_list, name='task_mapping_list'),
    path('<int:job_id>/create-estimate/', views.estimate_create_for_job, name='estimate_create_for_job'),
]