from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from apps.contacts.models import Contact, Business, PaymentTerms
from apps.jobs.models import Job, Estimate, Task, WorkOrder
from apps.invoicing.models import Invoice, LineItem, ItemType, PriceListItem
from apps.purchasing.models import PurchaseOrder, Bill
from apps.core.models import User


class Command(BaseCommand):
    help = 'Create extended test data for webserver development'

    def handle(self, *args, **options):
        self.stdout.write('Creating extended test data...')
        
        # Create payment terms first
        payment_terms = self.create_payment_terms()
        
        # Create Housing Supply business and contact
        housing_contact, housing_business = self.create_housing_supply(payment_terms)
        
        # Create businesses for existing contacts
        self.create_businesses_for_contacts(payment_terms)
        
        # Create item types and price list items
        item_types = self.create_item_types()
        price_list_items = self.create_price_list_items(item_types)
        
        # Get existing jobs
        jobs = Job.objects.all().order_by('job_id')
        
        # Create estimates for non-draft jobs
        estimates = self.create_estimates(jobs)
        
        # Create invoices for complete jobs
        invoices = self.create_invoices(jobs)
        
        # Create line items for estimates and invoices
        self.create_line_items(estimates, invoices, price_list_items)
        
        # Create work orders and tasks
        self.create_work_orders_and_tasks(jobs)
        
        # Create PO and Bill for job 1
        self.create_po_and_bill(jobs[0], housing_contact, price_list_items)
        
        self.stdout.write(self.style.SUCCESS('Extended test data created successfully!'))

    def create_payment_terms(self):
        terms, created = PaymentTerms.objects.get_or_create(term_id=1)
        if created:
            self.stdout.write('  Created payment terms')
        return terms

    def create_housing_supply(self, payment_terms):
        contact, created = Contact.objects.get_or_create(
            email='orders@housingsupply.com',
            defaults={
                'name': 'Housing Supply Co.',
                'phone': '555-0606',
                'address': '888 Supply Drive, Industrial District, City, State 12350'
            }
        )
        if created:
            self.stdout.write('  Created Housing Supply contact')
            
        business, created = Business.objects.get_or_create(
            business_name='Housing Supply',
            defaults={
                'our_reference_code': 'HS001',
                'business_number': 'BN-789012',
                'business_address': '888 Supply Drive, Industrial District, City, State 12350',
                'tax_exemption_number': 'TEX-456789',
                'term_id': payment_terms
            }
        )
        if created:
            self.stdout.write('  Created Housing Supply business')
            
        return contact, business

    def create_businesses_for_contacts(self, payment_terms):
        # ABC Construction Co.
        contact = Contact.objects.get(name='ABC Construction Co.')
        business, created = Business.objects.get_or_create(
            business_name='ABC Construction Co.',
            defaults={
                'our_reference_code': 'ABC001',
                'business_number': 'BN-123456',
                'business_address': contact.address,
                'tax_exemption_number': 'TEX-123456',
                'term_id': payment_terms
            }
        )
        if created:
            self.stdout.write('  Created ABC Construction business')

        # Metro Office Complex
        contact = Contact.objects.get(name='Metro Office Complex')
        business, created = Business.objects.get_or_create(
            business_name='Metro Office Complex',
            defaults={
                'our_reference_code': 'MOC001',
                'business_number': 'BN-345678',
                'business_address': contact.address,
                'tax_exemption_number': 'TEX-345678',
                'term_id': payment_terms
            }
        )
        if created:
            self.stdout.write('  Created Metro Office business')

        # Industrial Solutions Inc.
        contact = Contact.objects.get(name='Industrial Solutions Inc.')
        business, created = Business.objects.get_or_create(
            business_name='Industrial Solutions Inc.',
            defaults={
                'our_reference_code': 'ISI001',
                'business_number': 'BN-567890',
                'business_address': contact.address,
                'tax_exemption_number': 'TEX-567890',
                'term_id': payment_terms
            }
        )
        if created:
            self.stdout.write('  Created Industrial Solutions business')

    def create_item_types(self):
        item_types = {}
        
        types_data = [
            {'name': 'Labor', 'taxability': 'taxable', 'mapping_to_task': 'labor'},
            {'name': 'Materials', 'taxability': 'taxable', 'mapping_to_task': 'materials'},
            {'name': 'Equipment', 'taxability': 'taxable', 'mapping_to_task': 'equipment'},
            {'name': 'Supplies', 'taxability': 'taxable', 'mapping_to_task': 'supplies'}
        ]
        
        for type_data in types_data:
            item_type, created = ItemType.objects.get_or_create(
                name=type_data['name'],
                defaults=type_data
            )
            item_types[type_data['name']] = item_type
            if created:
                self.stdout.write(f'  Created item type: {type_data["name"]}')
                
        return item_types

    def create_price_list_items(self, item_types):
        price_list_items = []
        
        items_data = [
            {'code': 'LAB001', 'description': 'General Labor - per hour', 'type': 'Labor', 'unit': 'hour', 'purchase': 25.00, 'selling': 45.00},
            {'code': 'LAB002', 'description': 'Skilled Labor - per hour', 'type': 'Labor', 'unit': 'hour', 'purchase': 35.00, 'selling': 65.00},
            {'code': 'MAT001', 'description': 'Drywall - per sheet', 'type': 'Materials', 'unit': 'sheet', 'purchase': 12.00, 'selling': 18.00},
            {'code': 'MAT002', 'description': 'Paint - per gallon', 'type': 'Materials', 'unit': 'gallon', 'purchase': 25.00, 'selling': 40.00},
            {'code': 'MAT003', 'description': 'Flooring - per sq ft', 'type': 'Materials', 'unit': 'sq ft', 'purchase': 3.50, 'selling': 6.00},
            {'code': 'EQP001', 'description': 'Tool Rental - per day', 'type': 'Equipment', 'unit': 'day', 'purchase': 15.00, 'selling': 25.00},
            {'code': 'SUP001', 'description': 'Screws and Fasteners', 'type': 'Supplies', 'unit': 'box', 'purchase': 8.00, 'selling': 15.00},
        ]
        
        for item_data in items_data:
            item, created = PriceListItem.objects.get_or_create(
                code=item_data['code'],
                defaults={
                    'item_type_id': item_types[item_data['type']],
                    'unit_parts_labor': item_data['unit'],
                    'description': item_data['description'],
                    'purchase_price': Decimal(str(item_data['purchase'])),
                    'selling_price': Decimal(str(item_data['selling'])),
                    'qty_on_hand': Decimal('100.00'),
                    'qty_sold': Decimal('0.00'),
                    'qty_wasted': Decimal('0.00')
                }
            )
            price_list_items.append(item)
            if created:
                self.stdout.write(f'  Created price list item: {item_data["code"]}')
                
        return price_list_items

    def create_estimates(self, jobs):
        estimates = []
        estimate_counter = 1
        
        for job in jobs:
            if job.status != 'draft':
                # Create 1-2 estimates per job
                num_estimates = 2 if job.status == 'complete' else 1
                
                for i in range(num_estimates):
                    revision = i + 1
                    status = 'accepted' if job.status == 'complete' and revision == 2 else 'open'
                    if job.status == 'rejected':
                        status = 'rejected'
                    
                    estimate, created = Estimate.objects.get_or_create(
                        estimate_number=f'EST-2024-{estimate_counter:03d}',
                        defaults={
                            'job_id': job,
                            'revision_number': revision,
                            'status': status
                        }
                    )
                    estimates.append(estimate)
                    if created:
                        self.stdout.write(f'  Created estimate: {estimate.estimate_number}')
                    estimate_counter += 1
                    
        return estimates

    def create_invoices(self, jobs):
        invoices = []
        invoice_counter = 1
        
        for job in jobs:
            if job.status == 'complete':
                invoice, created = Invoice.objects.get_or_create(
                    invoice_number=f'INV-2024-{invoice_counter:03d}',
                    defaults={
                        'job_id': job,
                        'status': 'active'
                    }
                )
                invoices.append(invoice)
                if created:
                    self.stdout.write(f'  Created invoice: {invoice.invoice_number}')
                invoice_counter += 1
                
        return invoices

    def create_line_items(self, estimates, invoices, price_list_items):
        line_item_counter = 1
        
        # Create line items for estimates
        for estimate in estimates:
            # 2-4 line items per estimate
            num_items = 3 if estimate.job_id.status == 'complete' else 2
            
            for i in range(num_items):
                price_item = price_list_items[i % len(price_list_items)]
                qty = Decimal('10.00') if i == 0 else Decimal('5.00')
                
                line_item, created = LineItem.objects.get_or_create(
                    central_line_item_number=f'LI-EST-{line_item_counter:03d}',
                    defaults={
                        'estimate_id': estimate,
                        'price_list_item_id': price_item,
                        'qty': qty,
                        'unit_parts_labor': price_item.unit_parts_labor,
                        'description': price_item.description,
                        'price_currency': price_item.selling_price
                    }
                )
                if created:
                    self.stdout.write(f'  Created estimate line item: {line_item.central_line_item_number}')
                line_item_counter += 1
        
        # Create line items for invoices
        for invoice in invoices:
            # 3-4 line items per invoice
            for i in range(3):
                price_item = price_list_items[i % len(price_list_items)]
                qty = Decimal('8.00') if i == 0 else Decimal('4.00')
                
                line_item, created = LineItem.objects.get_or_create(
                    central_line_item_number=f'LI-INV-{line_item_counter:03d}',
                    defaults={
                        'invoice_id': invoice,
                        'price_list_item_id': price_item,
                        'qty': qty,
                        'unit_parts_labor': price_item.unit_parts_labor,
                        'description': price_item.description,
                        'price_currency': price_item.selling_price
                    }
                )
                if created:
                    self.stdout.write(f'  Created invoice line item: {line_item.central_line_item_number}')
                line_item_counter += 1

    def create_work_orders_and_tasks(self, jobs):
        task_counter = 1
        
        # Skip one of the draft jobs (job 8)
        jobs_with_tasks = [job for job in jobs if not (job.status == 'draft' and job.job_number == 'JOB-2024-008')]
        
        for job in jobs_with_tasks:
            # Create a work order for the job
            work_order, created = WorkOrder.objects.get_or_create(
                job_id=job,
                defaults={
                    'status': 'complete' if job.status == 'complete' else 'incomplete',
                    'estimated_time': timedelta(hours=8)
                }
            )
            if created:
                self.stdout.write(f'  Created work order for job {job.job_number}')
            
            # Create 2-3 tasks per work order
            task_names = [
                'Site preparation and setup',
                'Material procurement and delivery',
                'Installation and construction work',
                'Quality inspection and cleanup'
            ]
            
            num_tasks = 3 if job.status in ['complete', 'approved'] else 2
            
            for i in range(num_tasks):
                task, created = Task.objects.get_or_create(
                    name=task_names[i],
                    work_order=work_order,
                    defaults={
                        'task_type': 'installation' if i == 2 else 'preparation'
                    }
                )
                if created:
                    self.stdout.write(f'  Created task: {task.name}')
                task_counter += 1

    def create_po_and_bill(self, job, housing_contact, price_list_items):
        # Create purchase order for job 1
        po, created = PurchaseOrder.objects.get_or_create(
            po_number='PO-2024-001',
            defaults={
                'job_id': job,
                'price_list_item_id': price_list_items[2].code  # MAT001 - Drywall
            }
        )
        if created:
            self.stdout.write(f'  Created purchase order: {po.po_number}')
        
        # Create bill for the purchase order
        bill, created = Bill.objects.get_or_create(
            vendor_invoice_number='HS-INV-001',
            defaults={
                'po_id': po,
                'contact_id': housing_contact
            }
        )
        if created:
            self.stdout.write(f'  Created bill for PO: {bill.vendor_invoice_number}')
        
        # Create line items for the bill
        line_item, created = LineItem.objects.get_or_create(
            central_line_item_number='LI-BILL-001',
            defaults={
                'bill_id': bill,
                'price_list_item_id': price_list_items[2],  # Drywall
                'qty': Decimal('50.00'),
                'unit_parts_labor': 'sheet',
                'description': 'Drywall sheets for office renovation',
                'price_currency': Decimal('12.00')
            }
        )
        if created:
            self.stdout.write(f'  Created bill line item: {line_item.central_line_item_number}')