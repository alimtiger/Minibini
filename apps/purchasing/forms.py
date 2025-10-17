from django import forms
from .models import PurchaseOrder, PurchaseOrderLineItem
from apps.contacts.models import Business
from apps.invoicing.models import PriceListItem
from apps.core.services import NumberGenerationService


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating/editing PurchaseOrder"""
    business = forms.ModelChoiceField(
        queryset=Business.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Business --"
    )

    class Meta:
        model = PurchaseOrder
        fields = ['business', 'job']
        help_texts = {
            'job': 'PO number will be assigned automatically on save.',
        }

    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)

        # Job is optional, but if provided, pre-select it
        self.fields['job'].required = False
        if job:
            self.fields['job'].initial = job

    def save(self, commit=True):
        """Override save to generate PO number using NumberGenerationService"""
        instance = super().save(commit=False)

        # Generate the actual PO number (increments counter)
        instance.po_number = NumberGenerationService.generate_next_number('po')

        if commit:
            instance.save()
        return instance


class PurchaseOrderLineItemForm(forms.Form):
    """Form for creating a PO line item from a Price List Item"""
    price_list_item = forms.ModelChoiceField(
        queryset=PriceListItem.objects.all(),
        required=True,
        label="Price List Item"
    )
    qty = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=1.0,
        widget=forms.NumberInput(attrs={'step': '0.01'}),
        label="Quantity"
    )
