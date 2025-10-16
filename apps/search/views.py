from django.shortcuts import render
from django.db.models import Q, Value
from django.db.models.functions import Cast, Concat
from django.db.models import CharField
from apps.jobs.models import Job, Estimate, Task, WorkOrder, EstWorksheet, EstimateLineItem
from apps.contacts.models import Contact, Business
from apps.invoicing.models import Invoice, InvoiceLineItem, PriceListItem
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLineItem, Bill, BillLineItem


def search_view(request):
    """
    Search across all models and return categorized results.
    Case-insensitive search across relevant fields.
    Results are organized into supercategories with subcategories for line items.
    """
    query = request.GET.get('q', '').strip()

    context = {
        'query': query,
        'categories': {},
        'total_count': 0,
    }

    if not query:
        return render(request, 'search/search_results.html', context)

    # Initialize categories
    categories = {}

    # BUSINESSES
    businesses = Business.objects.filter(
        Q(business_name__icontains=query) |
        Q(our_reference_code__icontains=query) |
        Q(business_address__icontains=query) |
        Q(business_number__icontains=query)
    )
    if businesses.exists():
        categories['Businesses'] = {
            'items': businesses,
            'subcategories': {}
        }

    # PRICE LIST ITEMS
    price_list_items = PriceListItem.objects.annotate(
        purchase_price_text=Cast('purchase_price', CharField()),
        selling_price_text=Cast('selling_price', CharField())
    ).filter(
        Q(code__icontains=query) |
        Q(description__icontains=query) |
        Q(units__icontains=query) |
        Q(purchase_price_text__icontains=query) |
        Q(selling_price_text__icontains=query)
    )
    if price_list_items.exists():
        categories['Price List Items'] = {
            'items': price_list_items,
            'subcategories': {}
        }

    # CONTACTS
    contacts = Contact.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(mobile_number__icontains=query) |
        Q(work_number__icontains=query) |
        Q(home_number__icontains=query) |
        Q(addr1__icontains=query) |
        Q(city__icontains=query) |
        Q(postal_code__icontains=query)
    ).select_related('business')
    if contacts.exists():
        categories['Contacts'] = {
            'items': contacts,
            'subcategories': {}
        }

    # INVOICES (with line items grouped by parent)
    invoices = Invoice.objects.filter(
        Q(invoice_number__icontains=query) |
        Q(job__job_number__icontains=query) |
        Q(job__customer_po_number__icontains=query)
    ).select_related('job').prefetch_related('invoicelineitem_set')

    invoice_line_items = InvoiceLineItem.objects.annotate(
        price_text=Cast('price_currency', CharField()),
        qty_text=Cast('qty', CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(invoice__invoice_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query)
    ).select_related('invoice', 'invoice__job')

    # Build a dict of invoices with their matching line items
    invoice_dict = {}
    for invoice in invoices:
        invoice_dict[invoice.invoice_id] = {
            'parent': invoice,
            'line_items': []
        }

    for line_item in invoice_line_items:
        invoice_id = line_item.invoice.invoice_id
        if invoice_id not in invoice_dict:
            invoice_dict[invoice_id] = {
                'parent': line_item.invoice,
                'line_items': []
            }
        invoice_dict[invoice_id]['line_items'].append(line_item)

    if invoice_dict:
        categories['Invoices'] = {
            'grouped_items': list(invoice_dict.values())
        }

    # JOBS
    jobs = Job.objects.filter(
        Q(job_number__icontains=query) |
        Q(customer_po_number__icontains=query) |
        Q(description__icontains=query) |
        Q(contact__name__icontains=query)
    ).select_related('contact')
    if jobs.exists():
        categories['Jobs'] = {
            'items': jobs,
            'subcategories': {}
        }

    # ESTIMATES (with line items grouped by parent)
    estimates = Estimate.objects.filter(
        Q(estimate_number__icontains=query) |
        Q(job__job_number__icontains=query)
    ).select_related('job').prefetch_related('estimatelineitem_set')

    estimate_line_items = EstimateLineItem.objects.annotate(
        price_text=Cast('price_currency', CharField()),
        qty_text=Cast('qty', CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(estimate__estimate_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query)
    ).select_related('estimate', 'estimate__job')

    # Build a dict of estimates with their matching line items
    estimate_dict = {}
    for estimate in estimates:
        estimate_dict[estimate.estimate_id] = {
            'parent': estimate,
            'line_items': []
        }

    for line_item in estimate_line_items:
        estimate_id = line_item.estimate.estimate_id
        if estimate_id not in estimate_dict:
            estimate_dict[estimate_id] = {
                'parent': line_item.estimate,
                'line_items': []
            }
        estimate_dict[estimate_id]['line_items'].append(line_item)

    if estimate_dict:
        categories['Estimates'] = {
            'grouped_items': list(estimate_dict.values())
        }

    # WORK ORDERS (with tasks grouped by parent)
    work_orders = WorkOrder.objects.filter(
        Q(job__job_number__icontains=query) |
        Q(job__description__icontains=query)
    ).select_related('job').prefetch_related('task_set')

    tasks = Task.objects.filter(
        Q(name__icontains=query) |
        Q(units__icontains=query) |
        Q(work_order__job__job_number__icontains=query)
    ).select_related('assignee', 'work_order', 'work_order__job', 'est_worksheet')

    # Build a dict of work orders with their matching tasks
    wo_dict = {}
    for wo in work_orders:
        wo_dict[wo.work_order_id] = {
            'parent': wo,
            'tasks': []
        }

    for task in tasks:
        if task.work_order:
            wo_id = task.work_order.work_order_id
            if wo_id not in wo_dict:
                wo_dict[wo_id] = {
                    'parent': task.work_order,
                    'tasks': []
                }
            wo_dict[wo_id]['tasks'].append(task)

    if wo_dict:
        categories['Work Orders'] = {
            'grouped_items': list(wo_dict.values())
        }

    # BILLS (with line items grouped by parent)
    bills = Bill.objects.filter(
        Q(vendor_invoice_number__icontains=query) |
        Q(purchase_order__po_number__icontains=query) |
        Q(contact__name__icontains=query)
    ).select_related('purchase_order', 'contact').prefetch_related('billlineitem_set')

    bill_line_items = BillLineItem.objects.annotate(
        price_text=Cast('price_currency', CharField()),
        qty_text=Cast('qty', CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(bill__vendor_invoice_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query)
    ).select_related('bill', 'bill__purchase_order', 'bill__contact')

    # Build a dict of bills with their matching line items
    bill_dict = {}
    for bill in bills:
        bill_dict[bill.bill_id] = {
            'parent': bill,
            'line_items': []
        }

    for line_item in bill_line_items:
        bill_id = line_item.bill.bill_id
        if bill_id not in bill_dict:
            bill_dict[bill_id] = {
                'parent': line_item.bill,
                'line_items': []
            }
        bill_dict[bill_id]['line_items'].append(line_item)

    if bill_dict:
        categories['Bills'] = {
            'grouped_items': list(bill_dict.values())
        }

    # PURCHASE ORDERS (with line items grouped by parent)
    purchase_orders = PurchaseOrder.objects.filter(
        Q(po_number__icontains=query) |
        Q(job__job_number__icontains=query)
    ).select_related('job').prefetch_related('purchaseorderlineitem_set')

    po_line_items = PurchaseOrderLineItem.objects.annotate(
        price_text=Cast('price_currency', CharField()),
        qty_text=Cast('qty', CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(purchase_order__po_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query)
    ).select_related('purchase_order', 'purchase_order__job')

    # Build a dict of purchase orders with their matching line items
    po_dict = {}
    for po in purchase_orders:
        po_dict[po.po_id] = {
            'parent': po,
            'line_items': []
        }

    for line_item in po_line_items:
        po_id = line_item.purchase_order.po_id
        if po_id not in po_dict:
            po_dict[po_id] = {
                'parent': line_item.purchase_order,
                'line_items': []
            }
        po_dict[po_id]['line_items'].append(line_item)

    if po_dict:
        categories['Purchase Orders'] = {
            'grouped_items': list(po_dict.values())
        }

    context['categories'] = categories

    # Calculate total count
    total = 0
    for category_data in categories.values():
        if 'items' in category_data:
            # Old structure (Jobs, Contacts, etc.)
            total += len(category_data['items'])
            if 'subcategories' in category_data:
                for subcategory_items in category_data['subcategories'].values():
                    total += len(subcategory_items)
        elif 'grouped_items' in category_data:
            # New structure (Invoices, Estimates, Work Orders, etc. with line items/tasks)
            for group in category_data['grouped_items']:
                total += 1  # Count the parent
                if 'line_items' in group:
                    total += len(group['line_items'])  # Count the line items
                if 'tasks' in group:
                    total += len(group['tasks'])  # Count the tasks

    context['total_count'] = total

    return render(request, 'search/search_results.html', context)
