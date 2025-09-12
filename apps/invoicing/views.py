from django.shortcuts import render, get_object_or_404
from .models import Invoice, InvoiceLineItem

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