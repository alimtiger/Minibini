from django.db import models
from apps.core.models import BaseLineItem


class PurchaseOrder(models.Model):
    po_id = models.AutoField(primary_key=True)
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, null=True, blank=True)
    price_list_item = models.ForeignKey('invoicing.PriceListItem', on_delete=models.CASCADE, null=True, blank=True)
    po_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"PO {self.po_number}"


class Bill(models.Model):
    bill_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    vendor_invoice_number = models.CharField(max_length=50)

    def __str__(self):
        return f"Bill {self.bill_id}"


class PurchaseOrderLineItem(BaseLineItem):
    """Line item for purchase orders - inherits shared functionality from BaseLineItem."""
    
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Purchase Order Line Item"
        verbose_name_plural = "Purchase Order Line Items"
    
    def __str__(self):
        return f"PO Line Item {self.line_item_id} for {self.purchase_order.po_number}"


class BillLineItem(BaseLineItem):
    """Line item for bills - inherits shared functionality from BaseLineItem."""
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Bill Line Item"
        verbose_name_plural = "Bill Line Items"
    
    def __str__(self):
        return f"Bill Line Item {self.line_item_id} for Bill {self.bill.bill_id}"