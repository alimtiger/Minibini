# TaskTemplate Quantity Refactoring

## Overview

This document describes the refactoring of the TaskTemplate quantity system to support flexible quantities per WorkOrderTemplate association. The change addresses the limitation where TaskTemplates had fixed quantities that couldn't be customized based on project requirements.

## Problem Statement

The original system had TaskTemplates with fixed `est_qty` values that were applied regardless of the WorkOrderTemplate context. This caused issues such as:

- A "CAD Design" TaskTemplate with 8 hours was too much for a simple table but insufficient for a complex kitchen
- Users needed to create duplicate TaskTemplates for different project sizes
- No way to customize quantities when associating TaskTemplates with WorkOrderTemplates

## Solution: TemplateTaskAssociation Model

### Architecture Changes

**Before:**
```
TaskTemplate.est_qty → Task.est_qty → EstimateLineItem.qty
```

**After:**
```
TemplateTaskAssociation.est_qty → Task.est_qty → EstimateLineItem.qty
```

### New Model Structure

```python
class TemplateTaskAssociation(models.Model):
    """Association between WorkOrderTemplate and TaskTemplate with customizable quantities"""
    work_order_template = models.ForeignKey(WorkOrderTemplate, on_delete=models.CASCADE)
    task_template = models.ForeignKey('TaskTemplate', on_delete=models.CASCADE)
    est_qty = models.DecimalField(max_digits=10, decimal_places=2)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['work_order_template', 'task_template']
        ordering = ['sort_order', 'task_template__template_name']
```

### Updated TaskTemplate Model

```python
class TaskTemplate(models.Model):
    template_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    units = models.CharField(max_length=50, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # REMOVED: est_qty field
    
    # Updated relationship
    work_order_templates = models.ManyToManyField(
        WorkOrderTemplate, 
        through='TemplateTaskAssociation', 
        related_name='task_templates'
    )
```

## Implementation Details

### Phase 1: Model Changes
- ✅ Created `TemplateTaskAssociation` model
- ✅ Removed `est_qty` field from TaskTemplate
- ✅ Updated TaskTemplate to use through model

### Phase 2: Business Logic Updates
- ✅ Updated `TaskTemplate.generate_task()` to require `est_qty` parameter
- ✅ Updated `WorkOrderTemplate.generate_tasks_for_worksheet()` to use association quantities
- ✅ Updated `WorkOrderService.create_from_template()` to use association model
- ✅ Updated forms and views to handle association with quantities

### Key Method Changes

**TaskTemplate.generate_task():**
```python
# Before
def generate_task(self, container, product_identifier=None, product_instance=None, assignee=None):
    task = Task.objects.create(
        # ...
        est_qty=self.est_qty,  # Fixed quantity from template
        # ...
    )

# After  
def generate_task(self, container, est_qty, product_identifier=None, product_instance=None, assignee=None):
    task = Task.objects.create(
        # ...
        est_qty=est_qty,  # Quantity passed from association
        # ...
    )
```

**WorkOrderTemplate.generate_tasks_for_worksheet():**
```python
# Before
root_templates = self.tasktemplate_set.filter(...)
for task_template in root_templates:
    task = task_template.generate_task(worksheet, ...)

# After
associations = TemplateTaskAssociation.objects.filter(
    work_order_template=self,
    task_template__is_active=True
).order_by('sort_order', 'task_template__template_name')

for association in associations:
    task = association.task_template.generate_task(
        worksheet,
        est_qty=association.est_qty,  # Use association quantity
        ...
    )
```

### UI Changes

**WorkOrderTemplate Detail Page:**
- Shows association quantities instead of TaskTemplate quantities
- Includes quantity input field when associating TaskTemplates
- Displays tasks in sort order

**TaskTemplate List Page:**
- Removed quantity column (no longer relevant at template level)
- Shows which WorkOrderTemplates use each TaskTemplate

**Association Form:**
```html
<form method="post">
    <div>
        <label for="task_template_id">Task Template:</label>
        <select name="task_template_id" required>...</select>
    </div>
    <div>
        <label for="est_qty">Estimated Quantity:</label>
        <input type="number" name="est_qty" step="0.01" value="1.00" min="0" required>
    </div>
    <button type="submit" name="associate_task">Associate Task Template</button>
</form>
```

## Benefits Achieved

### 🎯 Flexible Quantities
TaskTemplates can now have different quantities per WorkOrderTemplate:
- **CAD Design TaskTemplate:**
  - Table WorkOrderTemplate: 5 hours
  - Kitchen WorkOrderTemplate: 20 hours  
  - Simple Repair WorkOrderTemplate: 2 hours

### 🎯 No Duplication
- One TaskTemplate can be reused across many WorkOrderTemplates
- No need to create duplicate templates for different project sizes
- Cleaner template management

### 🎯 Clean Separation
- **TaskTemplate**: Defines what the task is (rate, units, task mapping)
- **TemplateTaskAssociation**: Defines how much of the task is needed for a specific WorkOrderTemplate

### 🎯 Ordered Workflow
- Tasks within WorkOrderTemplates can be ordered using `sort_order`
- Predictable task sequence during worksheet generation

## Data Migration

### Fixture Updates
Updated both `webserver_test_data.json` and `unit_test_data.json`:

**Before:**
```json
{
  "model": "jobs.tasktemplate_work_order_templates",
  "pk": 1,
  "fields": {
    "tasktemplate": 1,
    "workordertemplate": 1
  }
}
```

**After:**
```json
{
  "model": "jobs.templatetaskassociation",
  "pk": 1,
  "fields": {
    "work_order_template": 1,
    "task_template": 1,
    "est_qty": "4.00",
    "sort_order": 1
  }
}
```

### Example Quantities in Fixtures

**webserver_test_data.json** (Furniture WorkOrderTemplate):
- Research: 4.00 hours
- CAD Design: 5.00 hours  
- Cut Parts: 300.00 minutes
- Assembly: 6.00 hours
- Finishing: 10.00 hours
- Delivery: 2.00 hours

**unit_test_data.json** (Test template):
- Site Preparation: 1.00 days
- Material Delivery: 2.00 loads
- Electrical Installation: 150.00 linear_feet
- Construction Work: 200.00 square_feet

## Future Enhancements

### Phase 3: Task-Level Quantity Overrides
The foundation is now in place for allowing users to override quantities when creating individual Tasks in EstWorksheets or WorkOrders:

```
TemplateTaskAssociation.est_qty (default) → User Override → Task.est_qty
```

### Phase 4: Advanced Features
- Bulk quantity adjustments
- Template cloning with quantity modifications
- Quantity validation rules
- Historical quantity tracking

## Testing Notes

All existing tests have been updated to work with the new association model:
- TaskTemplate creation tests no longer include `est_qty`
- Association-based quantity testing added
- Fixture loading tests updated for new model structure

## Breaking Changes

⚠️ **This is a breaking change** for any code that:
- Accesses `TaskTemplate.est_qty` directly
- Creates TaskTemplates with `est_qty` parameter
- Relies on the old M2M relationship without through model

The refactoring removes these dependencies in favor of the more flexible association-based approach.