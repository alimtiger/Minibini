from django.db import models
from decimal import Decimal


class Invoice(models.Model):
    INVOICE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
    ]

    invoice_id = models.AutoField(primary_key=True)
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=50, unique=True)
    customer_po_number = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=INVOICE_STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Invoice {self.invoice_number}"


class LineItem(models.Model):
    line_item_id = models.AutoField(primary_key=True)
    estimate = models.ForeignKey('jobs.Estimate', on_delete=models.CASCADE, null=True, blank=True)
    purchase_order = models.ForeignKey('purchasing.PurchaseOrder', on_delete=models.CASCADE, null=True, blank=True)
    bill = models.ForeignKey('purchasing.Bill', on_delete=models.CASCADE, null=True, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, null=True, blank=True)
    task = models.ForeignKey('jobs.Task', on_delete=models.CASCADE, null=True, blank=True)
    price_list_item = models.ForeignKey('PriceListItem', on_delete=models.CASCADE, null=True, blank=True)
    central_line_item_number = models.CharField(max_length=50, blank=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    unit_parts_labor = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    price_currency = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Line Item {self.line_item_id}"


class PriceListItem(models.Model):
    price_list_item_id = models.AutoField(primary_key=True)
    item_type = models.ForeignKey('ItemType', on_delete=models.CASCADE)
    code = models.CharField(max_length=50)
    unit_parts_labor = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    qty_on_hand = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    qty_sold = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    qty_wasted = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.code} - {self.description[:50]}"


class ItemType(models.Model):
    item_type_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    taxability = models.CharField(max_length=50, blank=True)
    mapping_to_task = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name