from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.jobs.models import ProductBundlingRule, WorkOrderTemplate


class ProductBundlingRuleValidationTest(TestCase):
    """Test validation rules for ProductBundlingRule"""
    
    def setUp(self):
        """Set up test data"""
        # Create WorkOrderTemplate with base price
        self.template_with_price = WorkOrderTemplate.objects.create(
            template_name="Premium Table Template",
            description="High-end dining table template",
            template_type="product",
            product_type="furniture",
            base_price=Decimal('2500.00')
        )
        
        # Create WorkOrderTemplate without base price
        self.template_without_price = WorkOrderTemplate.objects.create(
            template_name="Basic Table Template", 
            description="Basic table template",
            template_type="product",
            product_type="furniture",
            base_price=None
        )
    
    def test_template_base_pricing_requires_template(self):
        """ProductBundlingRule with template_base pricing must have a work_order_template"""
        with self.assertRaises(ValidationError) as context:
            rule = ProductBundlingRule(
                rule_name="Invalid Template Base Rule",
                product_type="furniture",
                work_order_template=None,  # Missing template
                line_item_template="Custom Furniture",
                pricing_method="template_base"
            )
            rule.full_clean()
        
        self.assertIn("template_base pricing requires", str(context.exception))
    
    def test_template_base_pricing_requires_base_price(self):
        """ProductBundlingRule with template_base pricing must reference template with base_price"""
        with self.assertRaises(ValidationError) as context:
            rule = ProductBundlingRule(
                rule_name="Invalid Base Price Rule",
                product_type="furniture", 
                work_order_template=self.template_without_price,  # Template has no base_price
                line_item_template="Custom Furniture",
                pricing_method="template_base"
            )
            rule.full_clean()
        
        self.assertIn("base_price", str(context.exception))
    
    def test_valid_template_base_pricing(self):
        """ProductBundlingRule with template_base pricing should be valid when properly configured"""
        rule = ProductBundlingRule(
            rule_name="Valid Template Base Rule",
            product_type="furniture",
            work_order_template=self.template_with_price,  # Template has base_price
            line_item_template="Premium Custom Furniture", 
            pricing_method="template_base"
        )
        
        # Should not raise ValidationError
        try:
            rule.full_clean()
            rule.save()
            self.assertTrue(True, "Valid template_base rule should save successfully")
        except ValidationError:
            self.fail("Valid template_base rule should not raise ValidationError")
    
    def test_sum_components_pricing_without_template(self):
        """ProductBundlingRule with sum_components pricing should work without template"""
        rule = ProductBundlingRule(
            rule_name="Sum Components Rule",
            product_type="furniture",
            work_order_template=None,  # No template needed for sum_components
            line_item_template="Custom Furniture",
            pricing_method="sum_components"
        )
        
        # Should not raise ValidationError
        try:
            rule.full_clean()
            rule.save()
            self.assertTrue(True, "sum_components rule without template should save successfully")
        except ValidationError:
            self.fail("sum_components rule without template should not raise ValidationError")
    
    def test_sum_components_pricing_with_template(self):
        """ProductBundlingRule with sum_components pricing should work with template"""
        rule = ProductBundlingRule(
            rule_name="Sum Components with Template Rule",
            product_type="furniture",
            work_order_template=self.template_with_price,  # Template allowed but not required
            line_item_template="Custom Furniture",
            pricing_method="sum_components"
        )
        
        # Should not raise ValidationError
        try:
            rule.full_clean()
            rule.save()
            self.assertTrue(True, "sum_components rule with template should save successfully")
        except ValidationError:
            self.fail("sum_components rule with template should not raise ValidationError")
    
    def test_custom_calculation_pricing(self):
        """ProductBundlingRule with custom_calculation pricing should work"""
        rule = ProductBundlingRule(
            rule_name="Custom Calculation Rule",
            product_type="furniture",
            work_order_template=None,
            line_item_template="Custom Furniture",
            pricing_method="custom_calculation"
        )
        
        # Should not raise ValidationError
        try:
            rule.full_clean()
            rule.save()
            self.assertTrue(True, "custom_calculation rule should save successfully")
        except ValidationError:
            self.fail("custom_calculation rule should not raise ValidationError")