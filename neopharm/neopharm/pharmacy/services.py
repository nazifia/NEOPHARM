"""
Service layer for pharmacy operations.
This file contains business logic separated from views for better maintainability.
"""
import logging
from typing import Optional, Dict, Type, Union
from decimal import Decimal
from django.db import transaction, models
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from .models import (
    LpacemakerDrugs, NcapDrugs, OncologyPharmacy,
    Cart, Form, FormItem
)

logger = logging.getLogger('pharmacy')

# Type alias for Drug models
DrugModel = Union[LpacemakerDrugs, NcapDrugs, OncologyPharmacy]


class DrugService:
    """Service for handling drug-related operations across all drug types."""

    # Map drug types to their model classes
    DRUG_MODEL_MAP = {
        'lpacemaker': LpacemakerDrugs,
        'ncap': NcapDrugs,
        'oncology': OncologyPharmacy,
    }

    # Map model classes back to drug types
    MODEL_TYPE_MAP = {
        LpacemakerDrugs: 'lpacemaker',
        NcapDrugs: 'ncap',
        OncologyPharmacy: 'oncology',
    }

    @classmethod
    def get_model(cls, drug_type: str) -> Type[DrugModel]:
        """Get the model class for a drug type."""
        model = cls.DRUG_MODEL_MAP.get(drug_type.lower())
        if not model:
            raise ValueError(f"Invalid drug type: {drug_type}")
        return model

    @classmethod
    def get_drug_type(cls, model: Type[DrugModel]) -> str:
        """Get the drug type string for a model class."""
        return cls.MODEL_TYPE_MAP.get(model)

    @classmethod
    def get_drug(cls, drug_type: str, pk: int) -> DrugModel:
        """Get a drug instance by type and ID."""
        model = cls.get_model(drug_type)
        try:
            return model.objects.get(pk=pk)
        except ObjectDoesNotExist:
            raise ValueError(f"{drug_type.title()} drug with ID {pk} not found")

    @classmethod
    def search_drugs(cls, query: str = '', category: str = 'all') -> Dict[str, list]:
        """Search drugs across all types with optional category filtering."""
        results = {
            'lpacemaker': [],
            'ncap': [],
            'oncology': []
        }

        if not query and category == 'all':
            # Return all drugs for empty query
            for dtype, model in cls.DRUG_MODEL_MAP.items():
                results[dtype] = list(model.objects.all().order_by('name')[:50])
            return results

        search_filter = models.Q(name__icontains=query) | models.Q(brand__icontains=query)

        if category in ['all', 'lpacemaker']:
            results['lpacemaker'] = list(
                LpacemakerDrugs.objects.filter(search_filter).order_by('name')[:50]
            )

        if category in ['all', 'ncap']:
            results['ncap'] = list(
                NcapDrugs.objects.filter(search_filter).order_by('name')[:50]
            )

        if category in ['all', 'oncology']:
            results['oncology'] = list(
                OncologyPharmacy.objects.filter(search_filter).order_by('name')[:50]
            )

        return results

    @classmethod
    @transaction.atomic
    def update_stock(cls, drug_type: str, pk: int, quantity_change: int, operation: str = 'subtract') -> DrugModel:
        """
        Update drug stock atomically.
        
        Args:
            drug_type: Type of drug (lpacemaker/ncap/oncology)
            pk: Primary key of drug
            quantity_change: Amount to change stock by
            operation: 'subtract' or 'add'
        
        Returns:
            Updated drug instance
        
        Raises:
            ValueError: If insufficient stock or invalid operation
            TypeError: If quantity_change is invalid
        """
        if not isinstance(quantity_change, int) or quantity_change < 1:
            raise TypeError("quantity_change must be a positive integer")
            
        model = cls.get_model(drug_type)
        
        # Use select_for_update to prevent race conditions
        drug = model.objects.select_for_update().get(pk=pk)
        
        current_stock = drug.stock or 0
        
        if operation == 'subtract':
            if current_stock < quantity_change:
                raise ValueError(
                    f"Insufficient stock for {drug.name}. "
                    f"Available: {current_stock}, Requested: {quantity_change}"
                )
            new_stock = current_stock - quantity_change
        elif operation == 'add':
            new_stock = current_stock + quantity_change
        else:
            raise ValueError(f"Invalid operation: {operation}")
        
        if new_stock < 0:
            raise ValueError(f"Stock cannot be negative. New value would be: {new_stock}")
        
        drug.stock = new_stock
        drug.save()
        
        logger.info(
            f"Stock updated for {drug_type} {drug.name}: "
            f"{current_stock} -> {new_stock} ({operation} {quantity_change})"
        )
        
        return drug


class CartService:
    """Service for cart operations."""

    @staticmethod
    def get_user_cart(user):
        """Get all cart items for a user with optimized queries."""
        return Cart.objects.filter(user=user).select_related(
            'lpacemaker_drug', 'ncap_drug', 'oncology_drug'
        )

    @staticmethod
    @transaction.atomic
    def add_to_cart(user, drug_type: str, drug_id: int, quantity: int, unit: str = None) -> Cart:
        """
        Add or update cart item.
        
        Returns:
            Cart instance
        """
        drug = DrugService.get_drug(drug_type, drug_id)
        
        # Check if item already in cart
        cart_kwargs = {
            'user': user,
            f'{drug_type}_drug': drug,
        }
        
        cart_item, created = Cart.objects.get_or_create(**cart_kwargs)
        
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
            cart_item.price = drug.price
            cart_item.unit = unit or drug.unit
            
        # Validate before saving
        cart_item.full_clean()
        cart_item.save()
        
        logger.info(
            f"Cart updated: {user.username} {drug_type} {drug.name} "
            f"quantity {cart_item.quantity}"
        )
        
        return cart_item

    @staticmethod
    @transaction.atomic
    def remove_from_cart(user, cart_id: int) -> bool:
        """Remove cart item with proper validation."""
        try:
            cart_item = Cart.objects.get(id=cart_id, user=user)
            cart_item.delete()
            logger.info(f"Item removed from cart: {user.username} - {cart_id}")
            return True
        except Cart.DoesNotExist:
            logger.warning(f"Cart item {cart_id} not found for user {user.username}")
            return False

    @staticmethod
    @transaction.atomic
    def clear_cart(user):
        """Clear all cart items for a user."""
        count = Cart.objects.filter(user=user).count()
        Cart.objects.filter(user=user).delete()
        logger.info(f"Cart cleared for {user.username}: {count} items removed")
        return count

    @staticmethod
    def calculate_cart_total(user):
        """Calculate total price for user's cart."""
        cart_items = CartService.get_user_cart(user)
        return sum(item.subtotal for item in cart_items)


class FormService:
    """Service for form and receipt operations."""

    @staticmethod
    @transaction.atomic
    def create_form_from_cart(user, buyer_name: str = None, hospital_no: str = None, ncap_no: str = None):
        """
        Create a form from user's cart.
        
        Returns:
            Form instance
        """
        cart_items = CartService.get_user_cart(user)
        
        if not cart_items.exists():
            raise ValidationError("Cart is empty")
        
        # Calculate total
        total_amount = sum(item.subtotal for item in cart_items)
        
        # Create form
        form = Form.objects.create(
            total_amount=total_amount,
            buyer_name=buyer_name,
            hospital_no=hospital_no,
            ncap_no=ncap_no,
            dispensed_by=user
        )
        
        # Create form items
        for cart_item in cart_items:
            drug = cart_item.get_item
            drug_type = DrugService.MODEL_TYPE_MAP.get(type(drug))
            
            if drug_type:
                FormItem.objects.create(
                    form=form,
                    drug_name=drug.name,
                    drug_brand=drug.brand,
                    drug_type=drug_type.upper(),
                    unit=cart_item.unit,
                    quantity=cart_item.quantity,
                    price=drug.price,
                    subtotal=cart_item.subtotal
                )
            
            logger.info(f"Added item to form {form.form_id}: {drug.name}")
        
        # Clear cart
        cart_items.delete()
        
        logger.info(f"Form {form.form_id} created by {user.username} for {total_amount}")
        
        return form

    @staticmethod
    def get_form_stats():
        """Get basic statistics for forms."""
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta
        
        # Last 30 days stats
        last_30_days = timezone.now() - timedelta(days=30)
        
        recent_forms = Form.objects.filter(date__gte=last_30_days)
        
        return {
            'total_forms': Form.objects.count(),
            'recent_forms': recent_forms.count(),
            'recent_revenue': recent_forms.aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0.00'),
            'average_form_value': recent_forms.aggregate(
                avg=Sum('total_amount') / Count('id')
            )['avg'] or Decimal('0.00'),
        }


class ReportingService:
    """Service for generating reports and statistics."""

    @staticmethod
    def get_inventory_report():
        """Get comprehensive inventory report."""
        from django.db.models import Sum
        
        categories = {
            'lpacemaker': {
                'model': LpacemakerDrugs,
                'name': 'LPACEMAKER',
            },
            'ncap': {
                'model': NcapDrugs,
                'name': 'NCAP',
            },
            'oncology': {
                'model': OncologyPharmacy,
                'name': 'ONCOLOGY',
            }
        }
        
        report = {}
        total_value = Decimal('0')
        total_items = 0
        low_stock_items = 0
        
        for key, info in categories.items():
            model = info['model']
            items = model.objects.all()
            
            # Calculate totals
            category_value = sum(item.total_value for item in items)
            category_count = items.count()
            category_low_stock = sum(1 for item in items if item.is_low_stock)
            
            report[key] = {
                'name': info['name'],
                'count': category_count,
                'total_value': category_value,
                'low_stock_count': category_low_stock,
                'items': items,
            }
            
            total_value += category_value
            total_items += category_count
            low_stock_items += category_low_stock
        
        report['overall'] = {
            'total_value': total_value,
            'total_items': total_items,
            'low_stock_items': low_stock_items,
        }
        
        return report

    @staticmethod
    def get_sales_report(days: int = 30):
        """Get sales report for specified days."""
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # FormItem totals by drug type
        drug_type_totals = FormItem.objects.filter(
            form__date__gte=cutoff_date
        ).values('drug_type').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('subtotal'),
            item_count=Count('id')
        ).order_by('drug_type')
        
        # Daily totals
        daily_totals = FormItem.objects.filter(
            form__date__gte=cutoff_date
        ).extra({
            'date': 'date(pharmacy_form.date)'
        }).values('date').annotate(
            daily_revenue=Sum('subtotal'),
            daily_quantity=Sum('quantity')
        ).order_by('date')
        
        # Form-level stats
        forms_data = Form.objects.filter(
            date__gte=cutoff_date
        ).aggregate(
            total_forms=Count('id'),
            total_revenue=Sum('total_amount'),
            avg_form_value=Sum('total_amount') / Count('id')
        )
        
        return {
            'period_days': days,
            'drug_type_totals': list(drug_type_totals),
            'daily_totals': list(daily_totals),
            'forms_summary': forms_data,
        }
