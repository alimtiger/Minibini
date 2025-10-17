from django.urls import path
from . import views

app_name = 'purchasing'

urlpatterns = [
    path('purchase-orders/', views.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:po_id>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:po_id>/add-line-item/', views.purchase_order_add_line_item, name='purchase_order_add_line_item'),
    path('bills/', views.bill_list, name='bill_list'),
    path('bills/<int:bill_id>/', views.bill_detail, name='bill_detail'),
]