from django.shortcuts import render
from django.db.models import Q
from apps.jobs.models import Job, Estimate, Task, WorkOrder, EstWorksheet
from apps.contacts.models import Contact, Business
from apps.invoicing.models import Invoice, PriceListItem
from apps.purchasing.models import PurchaseOrder, Bill


def search_view(request):
    """
    Search across all models and return categorized results.
    Case-insensitive search across relevant fields.
    """
    query = request.GET.get('q', '').strip()

    context = {
        'query': query,
        'results': {
            'jobs': [],
            'estimates': [],
            'tasks': [],
            'work_orders': [],
            'est_worksheets': [],
            'contacts': [],
            'businesses': [],
            'invoices': [],
            'price_list_items': [],
            'purchase_orders': [],
            'bills': [],
        },
        'total_count': 0,
    }

    if not query:
        return render(request, 'search/search_results.html', context)

    # Search Jobs
    jobs = Job.objects.filter(
        Q(job_number__icontains=query) |
        Q(customer_po_number__icontains=query) |
        Q(description__icontains=query) |
        Q(contact__name__icontains=query)
    ).select_related('contact')
    context['results']['jobs'] = jobs

    # Search Estimates
    estimates = Estimate.objects.filter(
        Q(estimate_number__icontains=query) |
        Q(job__job_number__icontains=query)
    ).select_related('job')
    context['results']['estimates'] = estimates

    # Search Tasks
    tasks = Task.objects.filter(
        Q(name__icontains=query) |
        Q(units__icontains=query)
    ).select_related('assignee', 'work_order', 'est_worksheet')
    context['results']['tasks'] = tasks

    # Search Work Orders
    work_orders = WorkOrder.objects.filter(
        Q(job__job_number__icontains=query) |
        Q(job__description__icontains=query)
    ).select_related('job')
    context['results']['work_orders'] = work_orders

    # Search EstWorksheets
    est_worksheets = EstWorksheet.objects.filter(
        Q(job__job_number__icontains=query) |
        Q(estimate__estimate_number__icontains=query)
    ).select_related('job', 'estimate')
    context['results']['est_worksheets'] = est_worksheets

    # Search Contacts
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
    context['results']['contacts'] = contacts

    # Search Businesses
    businesses = Business.objects.filter(
        Q(business_name__icontains=query) |
        Q(our_reference_code__icontains=query) |
        Q(business_address__icontains=query) |
        Q(business_number__icontains=query)
    )
    context['results']['businesses'] = businesses

    # Search Invoices
    invoices = Invoice.objects.filter(
        Q(invoice_number__icontains=query) |
        Q(job__job_number__icontains=query) |
        Q(job__customer_po_number__icontains=query)
    ).select_related('job')
    context['results']['invoices'] = invoices

    # Search Price List Items
    price_list_items = PriceListItem.objects.filter(
        Q(code__icontains=query) |
        Q(description__icontains=query) |
        Q(units__icontains=query)
    )
    context['results']['price_list_items'] = price_list_items

    # Search Purchase Orders
    purchase_orders = PurchaseOrder.objects.filter(
        Q(po_number__icontains=query) |
        Q(job__job_number__icontains=query)
    ).select_related('job')
    context['results']['purchase_orders'] = purchase_orders

    # Search Bills
    bills = Bill.objects.filter(
        Q(vendor_invoice_number__icontains=query) |
        Q(purchase_order__po_number__icontains=query) |
        Q(contact__name__icontains=query)
    ).select_related('purchase_order', 'contact')
    context['results']['bills'] = bills

    # Calculate total count
    context['total_count'] = sum(len(results) for results in context['results'].values())

    return render(request, 'search/search_results.html', context)
