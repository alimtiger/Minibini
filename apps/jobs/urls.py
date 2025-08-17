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
]