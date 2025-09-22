from django import forms
from django.core.exceptions import ValidationError
from .models import (
    WorkOrderTemplate, TaskTemplate, TaskMapping,
    EstWorksheet, Task, Estimate, EstimateLineItem, Job
)


class WorkOrderTemplateForm(forms.ModelForm):
    class Meta:
        model = WorkOrderTemplate
        fields = ['template_name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class TaskTemplateForm(forms.ModelForm):
    task_mapping = forms.ModelChoiceField(
        queryset=TaskMapping.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Task Mapping (Optional) --"
    )
    
    class Meta:
        model = TaskTemplate
        fields = ['template_name', 'description', 'units', 'rate', 'task_mapping', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'units': forms.TextInput(attrs={'placeholder': 'e.g., hours, pieces'}),
            'rate': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
        }


class EstWorksheetForm(forms.ModelForm):
    """Form for creating/editing EstWorksheet"""
    class Meta:
        model = EstWorksheet
        fields = ['job', 'template', 'status']
        widgets = {
            'status': forms.Select(choices=EstWorksheet.EST_WORKSHEET_STATUS_CHOICES)
        }


class EstWorksheetFromTemplateForm(forms.Form):
    """Form for creating EstWorksheet from WorkOrderTemplate"""
    job = forms.ModelChoiceField(queryset=Job.objects.all(), required=True)
    template = forms.ModelChoiceField(
        queryset=WorkOrderTemplate.objects.filter(is_active=True),
        required=True,
        label="Work Order Template"
    )


class TaskForm(forms.ModelForm):
    """Form for creating/editing Task"""
    class Meta:
        model = Task
        fields = ['name', 'template', 'est_worksheet', 'est_qty', 'units', 'rate']
        widgets = {
            'est_qty': forms.NumberInput(attrs={'step': '0.01'}),
            'rate': forms.NumberInput(attrs={'step': '0.01'}),
        }


class TaskFromTemplateForm(forms.Form):
    """Form for adding Task from TaskTemplate"""
    template = forms.ModelChoiceField(
        queryset=TaskTemplate.objects.filter(is_active=True),
        required=True,
        label="Task Template"
    )
    est_qty = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=1.0,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )


class EstimateLineItemForm(forms.ModelForm):
    """Form for creating/editing EstimateLineItem"""
    class Meta:
        model = EstimateLineItem
        fields = ['line_number', 'description', 'qty', 'units', 'price_currency', 'task', 'price_list_item']
        widgets = {
            'qty': forms.NumberInput(attrs={'step': '0.01'}),
            'price_currency': forms.NumberInput(attrs={'step': '0.01'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        estimate = kwargs.pop('estimate', None)
        super().__init__(*args, **kwargs)
        if estimate:
            # Only show tasks from the estimate's job
            self.fields['task'].queryset = Task.objects.filter(
                est_worksheet__job=estimate.job
            )


class EstimateForm(forms.ModelForm):
    """Form for creating/editing Estimate"""
    class Meta:
        model = Estimate
        fields = ['estimate_number', 'status']
        widgets = {
            'status': forms.Select(choices=Estimate.ESTIMATE_STATUS_CHOICES)
        }

    def __init__(self, *args, **kwargs):
        job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)
        if job:
            # Generate next estimate number for this job
            existing_estimates = Estimate.objects.filter(job=job).order_by('-version')
            if existing_estimates.exists():
                latest = existing_estimates.first()
                # Use same number but increment version will be handled in view
                self.fields['estimate_number'].initial = latest.estimate_number
            else:
                # Generate new estimate number based on job
                self.fields['estimate_number'].initial = f"EST-{job.job_number}"


class EstimateStatusForm(forms.Form):
    """Form for changing Estimate status"""
    VALID_TRANSITIONS = {
        'draft': ['open', 'rejected'],
        'open': ['accepted', 'rejected', 'superseded'],
        'accepted': ['superseded'],
        'rejected': [],
        'superseded': []
    }

    status = forms.ChoiceField(choices=[], required=True)

    def __init__(self, *args, **kwargs):
        current_status = kwargs.pop('current_status', 'draft')
        super().__init__(*args, **kwargs)

        # Set valid status choices based on current status
        valid_statuses = self.VALID_TRANSITIONS.get(current_status, [])
        choices = [(current_status, f'{current_status.title()} (current)')]
        choices.extend([(s, s.title()) for s in valid_statuses])

        self.fields['status'].choices = choices
        self.fields['status'].initial = current_status

    def clean_status(self):
        status = self.cleaned_data['status']
        # Additional validation if needed
        return status