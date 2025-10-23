from django.shortcuts import render
from django.db.models import Q, Value, F
from django.db.models.functions import Cast, Concat
from django.db.models import CharField, DecimalField
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

    # Get filter parameters
    filter_category = request.GET.get('category', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    price_min = request.GET.get('price_min', '').strip()
    price_max = request.GET.get('price_max', '').strip()

    context = {
        'query': query,
        'categories': {},
        'total_count': 0,
        'filter_category': filter_category,
        'date_from': date_from,
        'date_to': date_to,
        'price_min': price_min,
        'price_max': price_max,
    }

    if not query:
        return render(request, 'search/search_results.html', context)

    # Initialize categories
    categories = {}

    # Parse price filter values
    price_min_value = None
    price_max_value = None
    if price_min:
        try:
            price_min_value = float(price_min)
        except ValueError:
            pass
    if price_max:
        try:
            price_max_value = float(price_max)
        except ValueError:
            pass

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
        Q(first_name__icontains=query) |
        Q(middle_initial__icontains=query) |
        Q(last_name__icontains=query) |
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
        qty_text=Cast('qty', CharField()),
        total_amount_calc=F('qty') * F('price_currency'),
        total_amount_text=Cast(F('qty') * F('price_currency'), CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(invoice__invoice_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query) |
        Q(total_amount_text__icontains=query)
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
        Q(contact__first_name__icontains=query) |
        Q(contact__middle_initial__icontains=query) |
        Q(contact__last_name__icontains=query)
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
        qty_text=Cast('qty', CharField()),
        total_amount_calc=F('qty') * F('price_currency'),
        total_amount_text=Cast(F('qty') * F('price_currency'), CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(estimate__estimate_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query) |
        Q(total_amount_text__icontains=query)
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

    tasks = Task.objects.annotate(
        rate_text=Cast('rate', CharField())
    ).filter(
        Q(name__icontains=query) |
        Q(units__icontains=query) |
        Q(rate_text__icontains=query) |
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
        Q(contact__first_name__icontains=query) |
        Q(contact__middle_initial__icontains=query) |
        Q(contact__last_name__icontains=query)
    ).select_related('purchase_order', 'contact').prefetch_related('billlineitem_set')

    bill_line_items = BillLineItem.objects.annotate(
        price_text=Cast('price_currency', CharField()),
        qty_text=Cast('qty', CharField()),
        total_amount_calc=F('qty') * F('price_currency'),
        total_amount_text=Cast(F('qty') * F('price_currency'), CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(bill__vendor_invoice_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query) |
        Q(total_amount_text__icontains=query)
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
        qty_text=Cast('qty', CharField()),
        total_amount_calc=F('qty') * F('price_currency'),
        total_amount_text=Cast(F('qty') * F('price_currency'), CharField())
    ).filter(
        Q(description__icontains=query) |
        Q(purchase_order__po_number__icontains=query) |
        Q(price_text__icontains=query) |
        Q(qty_text__icontains=query) |
        Q(units__icontains=query) |
        Q(total_amount_text__icontains=query)
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

    # Apply category filter
    if filter_category and filter_category != 'all':
        if filter_category in categories:
            categories = {filter_category: categories[filter_category]}
        else:
            categories = {}

    # Apply date and price filters for items with dates/prices
    from datetime import datetime
    from decimal import Decimal

    filtered_categories = {}
    for category_name, category_data in categories.items():
        if 'grouped_items' in category_data:
            # Filter grouped items (Invoices, Estimates, POs, Bills, Work Orders)
            filtered_groups = []
            for group in category_data['grouped_items']:
                parent = group['parent']

                # Apply date filter
                date_passes = True
                if date_from or date_to:
                    parent_date = None
                    if hasattr(parent, 'created_date'):
                        parent_date = parent.created_date

                    if parent_date:
                        if date_from:
                            try:
                                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                                if parent_date.date() < date_from_obj:
                                    date_passes = False
                            except ValueError:
                                pass
                        if date_to:
                            try:
                                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                                if parent_date.date() > date_to_obj:
                                    date_passes = False
                            except ValueError:
                                pass

                # Apply price filter on line items
                if 'line_items' in group and (price_min_value is not None or price_max_value is not None):
                    filtered_line_items = []
                    for line_item in group['line_items']:
                        total = line_item.total_amount
                        price_passes = True
                        if price_min_value is not None and total < Decimal(str(price_min_value)):
                            price_passes = False
                        if price_max_value is not None and total > Decimal(str(price_max_value)):
                            price_passes = False
                        if price_passes:
                            filtered_line_items.append(line_item)
                    group['line_items'] = filtered_line_items
                    # Only include parent if it has matching line items or if no price filter
                    if date_passes and (filtered_line_items or not (price_min_value or price_max_value)):
                        filtered_groups.append(group)
                elif date_passes:
                    filtered_groups.append(group)

            if filtered_groups:
                filtered_categories[category_name] = {
                    'grouped_items': filtered_groups
                }
        elif 'items' in category_data:
            # For simple item categories (Jobs, Contacts, Businesses, Price List Items)
            # Apply date filter if applicable
            if date_from or date_to:
                filtered_items = []
                for item in category_data['items']:
                    date_passes = True
                    item_date = None
                    if hasattr(item, 'created_date'):
                        item_date = item.created_date

                    if item_date:
                        if date_from:
                            try:
                                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                                if item_date.date() < date_from_obj:
                                    date_passes = False
                            except ValueError:
                                pass
                        if date_to:
                            try:
                                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                                if item_date.date() > date_to_obj:
                                    date_passes = False
                            except ValueError:
                                pass

                    if date_passes:
                        filtered_items.append(item)

                if filtered_items:
                    filtered_categories[category_name] = {
                        'items': filtered_items,
                        'subcategories': category_data.get('subcategories', {})
                    }
            else:
                filtered_categories[category_name] = category_data

    context['categories'] = filtered_categories

    # Calculate total count
    total = 0
    for category_data in filtered_categories.values():
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

    # Add available categories for the filter dropdown
    all_category_names = ['Businesses', 'Price List Items', 'Contacts', 'Invoices', 'Jobs',
                          'Estimates', 'Work Orders', 'Bills', 'Purchase Orders']
    context['available_categories'] = all_category_names

    return render(request, 'search/search_results.html', context)
