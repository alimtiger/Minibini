from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from decimal import Decimal


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser with business-specific fields."""
    
    # Business-specific fields
    contact = models.OneToOneField(
        'contacts.Contact', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text='Associated contact record for this user'
    )
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'



class Configuration(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    field = models.CharField(max_length=255)
    invoice_number_sequence = models.CharField(max_length=50, blank=True)
    estimate_number_sequence = models.CharField(max_length=50, blank=True)
    job_number_sequence = models.CharField(max_length=50, blank=True)
    po_number_sequence = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"


class BaseLineItem(models.Model):
    """
    Abstract base class for all line item types.
    Provides shared functionality for EstimateLineItem, InvoiceLineItem, 
    PurchaseOrderLineItem, and BillLineItem.
    """
    line_item_id = models.AutoField(primary_key=True)
    task = models.ForeignKey('jobs.Task', on_delete=models.CASCADE, null=True, blank=True)
    price_list_item = models.ForeignKey('invoicing.PriceListItem', on_delete=models.CASCADE, null=True, blank=True)
    central_line_item_number = models.CharField(max_length=50, blank=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    unit_parts_labor = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    price_currency = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        abstract = True

    def clean(self):
        """Validate that line item cannot have both task and price_list_item."""
        super().clean()
        has_task = self.task is not None
        has_price_item = self.price_list_item is not None
        
        if has_task and has_price_item:
            raise ValidationError("LineItem cannot have both task and price_list_item")

    def save(self, *args, **kwargs):
        """Override save to ensure validation is always run."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Line Item {self.line_item_id}: {self.description[:50]}"

    @property
    def total_amount(self):
        """Calculate total amount (quantity * price)."""
        return self.qty * self.price_currency

    @property
    def source_name(self):
        """Get the name of the source (task name or price list item description)."""
        if self.task:
            return self.task.name
        elif self.price_list_item:
            return self.price_list_item.description
        return "No source"