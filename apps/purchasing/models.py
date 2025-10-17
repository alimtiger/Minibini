from django.db import models
from apps.core.models import BaseLineItem


class PurchaseOrder(models.Model):
    po_id = models.AutoField(primary_key=True)
    business = models.ForeignKey('contacts.Business', on_delete=models.CASCADE, null=True, blank=True)
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, null=True, blank=True)
    po_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"PO {self.po_number}"


class Bill(models.Model):
    bill_id = models.AutoField(primary_key=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    vendor_invoice_number = models.CharField(max_length=50)

    def __str__(self):
        return f"Bill {self.pk}"


class PurchaseOrderLineItem(BaseLineItem):
    """Line item for purchase orders - inherits shared functionality from BaseLineItem."""

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Purchase Order Line Item"
        verbose_name_plural = "Purchase Order Line Items"

    def get_parent_field_name(self):
        """Get the name of the parent field for this line item type."""
        return 'purchase_order'

    def __str__(self):
        return f"PO Line Item {self.pk} for {self.purchase_order.po_number}"


class BillLineItem(BaseLineItem):
    """Line item for bills - inherits shared functionality from BaseLineItem."""

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Bill Line Item"
        verbose_name_plural = "Bill Line Items"

    def get_parent_field_name(self):
        """Get the name of the parent field for this line item type."""
        return 'bill'

    def __str__(self):
        return f"Bill Line Item {self.pk} for Bill {self.bill.pk}"