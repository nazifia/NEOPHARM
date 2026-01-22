"""
Session-based cart functionality for NEOPHARM
Provides temporary cart storage in sessions and syncs with database when users authenticate
"""
import json
from decimal import Decimal
from django.utils import timezone
from .models import Cart, LpacemakerDrugs, NcapDrugs, OncologyPharmacy


class SessionCart:
    """Handle cart operations using session storage"""
    
    SESSION_KEY = 'temp_cart'
    CART_COUNT_KEY = 'cart_count'
    
    @classmethod
    def add_to_session_cart(cls, request, drug_type, drug_id, quantity=1):
        """Add item to session cart"""
        if not request.session.get(cls.SESSION_KEY):
            request.session[cls.SESSION_KEY] = {}
        
        cart = request.session[cls.SESSION_KEY]
        cart_id = f"{drug_type}_{drug_id}"
        
        if cart_id in cart:
            cart[cart_id]['quantity'] += quantity
        else:
            # Get drug details
            drug = cls._get_drug(drug_type, drug_id)
            if not drug:
                return False, "Drug not found"
            
            cart[cart_id] = {
                'drug_type': drug_type,
                'drug_id': drug_id,
                'name': drug.name,
                'brand': drug.brand,
                'price': float(drug.price),
                'quantity': quantity,
                'unit': getattr(drug, 'unit', 'N/A'),
                'stock': drug.stock,
                'added_at': timezone.now().isoformat()
            }
        
        request.session[cls.SESSION_KEY] = cart
        cls._update_cart_count(request)
        return True, "Item added to session cart"
    
    @classmethod
    def get_session_cart(cls, request):
        """Get session cart items"""
        return request.session.get(cls.SESSION_KEY, {})
    
    @classmethod
    def get_cart_count(cls, request):
        """Get total items in session cart"""
        cart = request.session.get(cls.SESSION_KEY, {})
        return sum(item['quantity'] for item in cart.values())
    
    @classmethod
    def remove_from_session_cart(cls, request, cart_id):
        """Remove item from session cart"""
        cart = request.session.get(cls.SESSION_KEY, {})
        if cart_id in cart:
            del cart[cart_id]
            request.session[cls.SESSION_KEY] = cart
            cls._update_cart_count(request)
            return True, "Item removed from session cart"
        return False, "Item not found in session cart"
    
    @classmethod
    def clear_session_cart(cls, request):
        """Clear entire session cart"""
        if cls.SESSION_KEY in request.session:
            del request.session[cls.SESSION_KEY]
        cls._update_cart_count(request, 0)
        return True, "Session cart cleared"
    
    @classmethod
    def calculate_session_cart_total(cls, request):
        """Calculate total price of items in session cart"""
        cart = request.session.get(cls.SESSION_KEY, {})
        total = Decimal('0')
        for item in cart.values():
            total += Decimal(str(item['price'])) * item['quantity']
        return total
    
    @classmethod
    def sync_session_cart_to_database(cls, request, user):
        """Move session cart items to database for authenticated user"""
        cart = request.session.get(cls.SESSION_KEY, {})
        transferred_count = 0
        
        for cart_id, item in cart.items():
            drug_type = item.get('drug_type')
            drug_id = item.get('drug_id')
            quantity = item.get('quantity')
            
            # Create database cart entry
            success, message = cls._create_db_cart_item(user, drug_type, drug_id, quantity)
            if success:
                transferred_count += 1
        
        # Clear session cart after successful sync
        if transferred_count > 0:
            cls.clear_session_cart(request)
        
        return transferred_count, f"Transferred {transferred_count} items to database cart"
    
    @classmethod
    def _create_db_cart_item(cls, user, drug_type, drug_id, quantity):
        """Create a database cart item from session data"""
        drug = cls._get_drug(drug_type, drug_id)
        if not drug:
            return False, "Drug not found"
        
        try:
            # Determine which foreign key to use based on drug type
            kwargs = {'user': user, 'quantity': quantity}
            if drug_type == 'lpacemaker':
                kwargs['lpacemaker_drug'] = drug
            elif drug_type == 'ncap':
                kwargs['ncap_drug'] = drug
            elif drug_type == 'oncology':
                kwargs['oncology_drug'] = drug
            
            # Get price and calculate subtotal
            price = Decimal(str(drug.price))
            subtotal = price * quantity
            
            # Create cart item
            cart_item = Cart.objects.create(
                price=price,
                subtotal=subtotal,
                total=subtotal,
                **kwargs
            )
            return True, f"Added {drug.name} to cart"
        except Exception as e:
            return False, str(e)
    
    @classmethod
    def _get_drug(cls, drug_type, drug_id):
        """Get drug object based on type"""
        try:
            if drug_type == 'lpacemaker':
                return LpacemakerDrugs.objects.get(pk=drug_id)
            elif drug_type == 'ncap':
                return NcapDrugs.objects.get(pk=drug_id)
            elif drug_type == 'oncology':
                return OncologyPharmacy.objects.get(pk=drug_id)
        except:
            return None
    
    @classmethod
    def _update_cart_count(cls, request, count=None):
        """Update cart count in session"""
        if count is None:
            count = cls.get_cart_count(request)
        request.session[cls.CART_COUNT_KEY] = count
    
    @classmethod
    def get_cart_count_from_session(cls, request):
        """Get cart count directly from session (for template use)"""
        return request.session.get(cls.CART_COUNT_KEY, 0)


class SessionCartMiddleware:
    """Middleware to handle session cart operations and provide cart count"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if user just logged in and has a session cart
        if request.user.is_authenticated and not hasattr(request, '_session_cart_processed'):
            session_cart_count = SessionCart.get_cart_count_from_session(request)
            if session_cart_count > 0:
                # Sync session cart to database
                transferred, message = SessionCart.sync_session_cart_to_database(request, request.user)
                if transferred > 0:
                    from django.contrib import messages
                    messages.success(request, f"{transferred} items transferred from browsing cart to your account")
                request._session_cart_processed = True
        
        # Set cart count in request for easy access
        request.cart_count = SessionCart.get_cart_count_from_session(request)
        
        response = self.get_response(request)
        
        # Ensure cart count is saved before response
        if hasattr(request, 'session'):
            SessionCart._update_cart_count(request)
        
        return response
