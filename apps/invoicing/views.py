from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Invoice, InvoiceLineItem, PriceListItem
from .forms import PriceListItemForm

def invoice_list(request):
    invoices = Invoice.objects.all().order_by('-invoice_id')
    return render(request, 'invoicing/invoice_list.html', {'invoices': invoices})

def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, invoice_id=invoice_id)
    line_items = InvoiceLineItem.objects.filter(invoice=invoice).order_by('line_item_id')
    # Calculate total amount
    total_amount = sum(item.total_amount for item in line_items)
    return render(request, 'invoicing/invoice_detail.html', {
        'invoice': invoice,
        'line_items': line_items,
        'total_amount': total_amount
    })


def price_list_item_list(request):
    """Display all price list items."""
    items = PriceListItem.objects.all().order_by('code')
    return render(request, 'invoicing/price_list_item_list.html', {
        'items': items
    })


def price_list_item_add(request):
    """Add a new price list item."""
    if request.method == 'POST':
        form = PriceListItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'Price List Item "{item.code}" created successfully.')
            return redirect('invoicing:price_list_item_list')
    else:
        form = PriceListItemForm()

    return render(request, 'invoicing/price_list_item_form.html', {
        'form': form,
        'title': 'Add Price List Item',
        'button_text': 'Create Item'
    })


def price_list_item_edit(request, item_id):
    """Edit an existing price list item."""
    item = get_object_or_404(PriceListItem, price_list_item_id=item_id)

    if request.method == 'POST':
        form = PriceListItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'Price List Item "{item.code}" updated successfully.')
            return redirect('invoicing:price_list_item_list')
    else:
        form = PriceListItemForm(instance=item)

    return render(request, 'invoicing/price_list_item_form.html', {
        'form': form,
        'item': item,
        'title': f'Edit Price List Item: {item.code}',
        'button_text': 'Update Item'
    })