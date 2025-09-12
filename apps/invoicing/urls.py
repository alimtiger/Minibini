from django.urls import path
from . import views

app_name = 'invoicing'

urlpatterns = [
    path('', views.invoice_list, name='invoice_list'),
    path('<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
]