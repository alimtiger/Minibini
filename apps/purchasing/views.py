from django.shortcuts import render, get_object_or_404
from .models import PurchaseOrder, Bill, BillLineItem, PurchaseOrderLineItem

def purchase_order_list(request):
    purchase_orders = PurchaseOrder.objects.all().order_by('-po_id')
    return render(request, 'purchasing/purchase_order_list.html', {'purchase_orders': purchase_orders})

def purchase_order_detail(request, po_id):
    purchase_order = get_object_or_404(PurchaseOrder, po_id=po_id)
    bills = Bill.objects.filter(purchase_order=purchase_order).order_by('-bill_id')
    line_items = PurchaseOrderLineItem.objects.filter(purchase_order=purchase_order).order_by('line_item_id')
    # Calculate total amount
    total_amount = sum(item.total_amount for item in line_items)
    return render(request, 'purchasing/purchase_order_detail.html', {
        'purchase_order': purchase_order, 
        'bills': bills,
        'line_items': line_items,
        'total_amount': total_amount
    })

def bill_list(request):
    bills = Bill.objects.all().order_by('-bill_id')
    return render(request, 'purchasing/bill_list.html', {'bills': bills})

def bill_detail(request, bill_id):
    bill = get_object_or_404(Bill, bill_id=bill_id)
    line_items = BillLineItem.objects.filter(bill=bill).order_by('line_item_id')
    # Calculate total amount
    total_amount = sum(item.total_amount for item in line_items)
    return render(request, 'purchasing/bill_detail.html', {
        'bill': bill,
        'line_items': line_items,
        'total_amount': total_amount
    })