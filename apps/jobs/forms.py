from django import forms
from .models import WorkOrderTemplate, TaskTemplate, TaskMapping


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
        fields = ['template_name', 'description', 'units', 'rate', 'est_qty', 'task_mapping', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'units': forms.TextInput(attrs={'placeholder': 'e.g., hours, pieces'}),
            'rate': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
            'est_qty': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
        }