from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import PurchaseOrder, Bill, BillLineItem, PurchaseOrderLineItem
from .forms import PurchaseOrderForm, PurchaseOrderLineItemForm

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

def purchase_order_create(request):
    """Create a new PurchaseOrder"""
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            purchase_order = form.save()
            messages.success(request, f'Purchase Order {purchase_order.po_number} created successfully.')
            return redirect('purchasing:purchase_order_detail', po_id=purchase_order.po_id)
    else:
        form = PurchaseOrderForm()

    return render(request, 'purchasing/purchase_order_create.html', {'form': form})

def purchase_order_add_line_item(request, po_id):
    """Add line item to PurchaseOrder from Price List"""
    purchase_order = get_object_or_404(PurchaseOrder, po_id=po_id)

    if request.method == 'POST':
        form = PurchaseOrderLineItemForm(request.POST)
        if form.is_valid():
            price_list_item = form.cleaned_data['price_list_item']
            qty = form.cleaned_data['qty']

            # Create line item from price list item, copying purchase_price
            line_item = PurchaseOrderLineItem.objects.create(
                purchase_order=purchase_order,
                price_list_item=price_list_item,
                description=price_list_item.description,
                qty=qty,
                units=price_list_item.units,
                price_currency=price_list_item.purchase_price  # Use purchase_price
            )

            messages.success(request, f'Line item "{line_item.description}" added from price list')
            return redirect('purchasing:purchase_order_detail', po_id=purchase_order.po_id)
    else:
        form = PurchaseOrderLineItemForm()

    return render(request, 'purchasing/purchase_order_add_line_item.html', {
        'form': form,
        'purchase_order': purchase_order
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