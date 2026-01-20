from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from .models import LpacemakerDrugs, NcapDrugs, OncologyPharmacy, Cart

class DrugService:
    @staticmethod
    def get_drug_model(drug_type):
        """Returns the model class based on drug_type string"""
        drug_type = drug_type.lower()
        if drug_type == 'lpacemaker':
            return LpacemakerDrugs
        elif drug_type == 'ncap':
            return NcapDrugs
        elif drug_type == 'oncology':
            return OncologyPharmacy
        raise ValueError(f"Invalid drug type: {drug_type}")

    @staticmethod
    def get_drug_field_name(drug_type):
        """Returns the field name for the drug relation in Cart model"""
        drug_type = drug_type.lower()
        if drug_type == 'lpacemaker':
            return 'lpacemaker_drug'
        elif drug_type == 'ncap':
            return 'ncap_drug'
        elif drug_type == 'oncology':
            return 'oncology_drug'
        raise ValueError(f"Invalid drug type: {drug_type}")

    @classmethod
    def get_drug(cls, drug_type, pk):
        model = cls.get_drug_model(drug_type)
        return get_object_or_404(model, pk=pk)

    @classmethod
    def add_to_cart(cls, user, drug_type, pk, quantity=1):
        """
        Adds an item to the user's cart.
        Returns a tuple (success, message, status_code).
        """
        try:
            with transaction.atomic():
                drug_model = cls.get_drug_model(drug_type)
                # Lock the row for update to prevent race conditions
                drug = drug_model.objects.select_for_update().get(pk=pk)
                
                if drug.stock < quantity:
                    return False, 'Insufficient stock', 400

                drug_field = cls.get_drug_field_name(drug_type)
                
                # Check for existing cart item
                cart_filter = {
                    'user': user,
                    'form__isnull': True,
                    drug_field: drug
                }
                
                cart_item = Cart.objects.filter(**cart_filter).first()
                
                if cart_item:
                    new_quantity = cart_item.quantity + quantity
                    if drug.stock < new_quantity:
                        return False, 'Insufficient stock', 400
                         
                    cart_item.quantity = new_quantity
                    cart_item.subtotal = cart_item.calculate_subtotal
                    cart_item.save()
                else:
                    # Create new cart item
                    cart_data = {
                        'user': user,
                        drug_field: drug,
                        'brand': drug.brand,
                        'unit': drug.unit,
                        'quantity': quantity,
                        'price': drug.price,
                        'subtotal': drug.price * quantity
                    }
                    Cart.objects.create(**cart_data)
                
                # Update stock safely using F expression
                drug.stock = F('stock') - quantity
                drug.save()
                drug.refresh_from_db() # Reload to get actual value after F update
                
                return True, f'Added {quantity} {drug.name} to cart', 200
                
        except (ValueError, drug_model.DoesNotExist):
             return False, 'Invalid item', 404
        except Exception as e:
            return False, str(e), 500

    @classmethod
    def return_item(cls, drug_type, pk, quantity):
        """
        Returns an item to stock.
        """
        try:
            with transaction.atomic():
                drug_model = cls.get_drug_model(drug_type)
                drug = drug_model.objects.select_for_update().get(pk=pk)
                
                drug.stock = F('stock') + quantity
                drug.save()
                
                return True, f'{drug.name} returned successfully!'
        except Exception as e:
            return False, str(e)
