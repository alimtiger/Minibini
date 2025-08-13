from django.db import models


class PurchaseOrder(models.Model):
    po_id = models.AutoField(primary_key=True)
    job_id = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, null=True, blank=True)
    price_list_item_id = models.CharField(max_length=50, blank=True)
    po_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"PO {self.po_number}"


class Bill(models.Model):
    bill_id = models.AutoField(primary_key=True)
    po_id = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    contact_id = models.ForeignKey('contacts.Contact', on_delete=models.CASCADE)
    vendor_invoice_number = models.CharField(max_length=50)

    def __str__(self):
        return f"Bill {self.bill_id}"