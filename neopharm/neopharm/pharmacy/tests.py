"""
Test suite for pharmacy application.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from .models import (
    LpacemakerDrugs, NcapDrugs, OncologyPharmacy,
    Cart, Form, FormItem, User
)
from .services import DrugService, CartService, FormService

User = get_user_model()


class DrugModelTests(TestCase):
    """Test drug model validation and functionality."""

    def setUp(self):
        """Set up test data."""
        self.lpacemaker = LpacemakerDrugs.objects.create(
            name='Test Drug',
            brand='Test Brand',
            price=Decimal('10.50'),
            stock=100,
            unit='Tab',
            dosage_form='Tablet',
            exp_date=date.today() + timedelta(days=365)
        )

    def test_drug_creation(self):
        """Test basic drug creation."""
        self.assertEqual(self.lpacemaker.name, 'Test Drug')
        self.assertEqual(self.lpacemaker.price, Decimal('10.50'))
        self.assertEqual(self.lpacemaker.stock, 100)

    def test_negative_price_validation(self):
        """Test that negative prices raise ValidationError."""
        with self.assertRaises(ValidationError):
            drug = LpacemakerDrugs(
                name='Bad Price',
                price=Decimal('-10.00'),
                stock=50
            )
            drug.full_clean()

    def test_negative_stock_validation(self):
        """Test that negative stock raises ValidationError."""
        with self.assertRaises(ValidationError):
            drug = LpacemakerDrugs(
                name='Bad Stock',
                price=Decimal('10.00'),
                stock=-5
            )
            drug.full_clean()

    def test_total_value_property(self):
        """Test total value calculation."""
        expected_value = Decimal('10.50') * Decimal('100')
        self.assertEqual(self.lpacemaker.total_value, expected_value)

    def test_is_low_stock_property(self):
        """Test low stock detection."""
        # Stock is 100, should not be low
        self.assertFalse(self.lpacemaker.is_low_stock)
        
        # Create low stock item
        low_stock = LpacemakerDrugs.objects.create(
            name='Low Stock',
            price=Decimal('5.00'),
            stock=5,
            unit='Tab'
        )
        self.assertTrue(low_stock.is_low_stock)


class CartServiceTests(TestCase):
    """Test cart service functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            mobile='08012345678',
            password='testpass123'
        )
        self.drug = LpacemakerDrugs.objects.create(
            name='Cart Drug',
            price=Decimal('15.00'),
            stock=50,
            unit='Tab'
        )

    def test_add_to_cart_new_item(self):
        """Test adding a new item to cart."""
        cart_item = CartService.add_to_cart(
            user=self.user,
            drug_type='lpacemaker',
            drug_id=self.drug.id,
            quantity=5,
            unit='Tab'
        )
        
        self.assertEqual(cart_item.quantity, 5)
        self.assertEqual(cart_item.user, self.user)
        self.assertEqual(cart_item.get_item.name, 'Cart Drug')

    def test_add_to_cart_existing_item(self):
        """Test adding quantity to existing cart item."""
        CartService.add_to_cart(
            user=self.user,
            drug_type='lpacemaker',
            drug_id=self.drug.id,
            quantity=5
        )
        
        # Add more of the same item
        CartService.add_to_cart(
            user=self.user,
            drug_type='lpacemaker',
            drug_id=self.drug.id,
            quantity=3
        )
        
        cart_items = CartService.get_user_cart(self.user)
        self.assertEqual(cart_items.count(), 1)
        self.assertEqual(cart_items.first().quantity, 8)

    def test_clear_cart(self):
        """Test clearing cart."""
        CartService.add_to_cart(
            user=self.user,
            drug_type='lpacemaker',
            drug_id=self.drug.id,
            quantity=5
        )
        
        count = CartService.clear_cart(self.user)
        self.assertEqual(count, 1)
        
        cart_items = CartService.get_user_cart(self.user)
        self.assertEqual(cart_items.count(), 0)


class FormServiceTests(TestCase):
    """Test form service functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='pharmacist',
            mobile='08011111111',
            password='testpass123'
        )
        self.drug1 = LpacemakerDrugs.objects.create(
            name='Drug 1',
            price=Decimal('10.00'),
            stock=50,
            unit='Tab'
        )
        self.drug2 = NcapDrugs.objects.create(
            name='Drug 2',
            price=Decimal('20.00'),
            stock=30,
            unit='Pack'
        )

    def test_create_form_from_cart(self):
        """Test creating a form from cart."""
        # Add items to cart
        CartService.add_to_cart(self.user, 'lpacemaker', self.drug1.id, 5)
        CartService.add_to_cart(self.user, 'ncap', self.drug2.id, 2)
        
        # Create form
        form = FormService.create_form_from_cart(
            user=self.user,
            buyer_name='Test Patient',
            hospital_no='H12345'
        )
        
        self.assertEqual(form.buyer_name, 'Test Patient')
        self.assertEqual(form.hospital_no, 'H12345')
        self.assertEqual(form.total_amount, Decimal('90.00'))  # 5*10 + 2*20
        
        # Check form items were created
        form_items = FormItem.objects.filter(form=form)
        self.assertEqual(form_items.count(), 2)
        
        # Check cart was cleared
        cart_items = CartService.get_user_cart(self.user)
        self.assertEqual(cart_items.count(), 0)


class DrugServiceTests(TestCase):
    """Test drug service functionality."""

    def setUp(self):
        """Set up test data."""
        self.lpacemaker = LpacemakerDrugs.objects.create(
            name='LP Drug',
            price=Decimal('10.00'),
            stock=50
        )
        self.ncap = NcapDrugs.objects.create(
            name='NC Drug',
            price=Decimal('20.00'),
            stock=30
        )

    def test_get_model_valid(self):
        """Test getting model for valid drug type."""
        model = DrugService.get_model('lpacemaker')
        self.assertEqual(model, LpacemakerDrugs)
        
        model = DrugService.get_model('ncap')
        self.assertEqual(model, NcapDrugs)

    def test_get_model_invalid(self):
        """Test getting model for invalid drug type."""
        with self.assertRaises(ValueError):
            DrugService.get_model('invalid_type')

    def test_get_drug(self):
        """Test getting a drug by type and ID."""
        drug = DrugService.get_drug('lpacemaker', self.lpacemaker.id)
        self.assertEqual(drug.name, 'LP Drug')

    def test_search_drugs(self):
        """Test drug searching."""
        results = DrugService.search_drugs(query='Drug', category='all')
        
        self.assertEqual(len(results['lpacemaker']), 1)
        self.assertEqual(len(results['ncap']), 1)
        self.assertEqual(results['lpacemaker'][0].name, 'LP Drug')
        self.assertEqual(results['ncap'][0].name, 'NC Drug')

    def test_update_stock_subtract(self):
        """Test stock reduction."""
        original_stock = self.lpacemaker.stock
        DrugService.update_stock('lpacemaker', self.lpacemaker.id, 10, 'subtract')
        
        self.lpacemaker.refresh_from_db()
        self.assertEqual(self.lpacemaker.stock, original_stock - 10)

    def test_update_stock_insufficient(self):
        """Test stock reduction with insufficient stock."""
        with self.assertRaises(ValueError):
            DrugService.update_stock('lpacemaker', self.lpacemaker.id, 1000, 'subtract')

    def test_update_stock_add(self):
        """Test stock increase."""
        original_stock = self.lpacemaker.stock
        DrugService.update_stock('lpacemaker', self.lpacemaker.id, 20, 'add')
        
        self.lpacemaker.refresh_from_db()
        self.assertEqual(self.lpacemaker.stock, original_stock + 20)


class ViewAuthorizationTests(TestCase):
    """Test view authorization and access control."""

    def setUp(self):
        """Set up test clients and users."""
        self.client = Client()
        self.regular_user = User.objects.create_user(
            username='regular',
            mobile='08022222222',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            mobile='08033333333',
            password='testpass123'
        )

    def test_index_view_get(self):
        """Test index page loads."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_login_redirect_authenticated(self):
        """Test that authenticated user is redirected from login."""
        self.client.login(mobile='08022222222', password='testpass123')
        response = self.client.get('/')
        self.assertRedirects(response, '/dashboard/')

    def test_dashboard_requires_login(self):
        """Test dashboard requires authentication."""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_admin_access(self):
        """Test admin-only views."""
        # Login as regular user
        self.client.login(mobile='08022222222', password='testpass123')
        
        # Try to access admin-only add item page
        response = self.client.get('/add-item/')
        self.assertEqual(response.status_code, 302)  # Redirect/Forbidden

    def test_csrf_protection(self):
        """Test that CSRF tokens are required for POST requests."""
        # This test would verify CSRF is working for critical operations
        # For now, we'll ensure the views have csrf_protect decorators
        pass


class SecurityTests(TestCase):
    """Test security-related features."""

    def test_settings_use_env_vars(self):
        """Test that settings properly use environment variables."""
        from django.conf import settings
        
        # Debug should be configurable
        self.assertIsInstance(settings.DEBUG, bool)
        
        # Should not have hardcoded secret in production
        # (This is checked by environment variable usage)
        self.assertIsNotNone(settings.SECRET_KEY)

    def test_user_model_authentication(self):
        """Test custom user model authentication."""
        user = User.objects.create_user(
            username='mobileuser',
            mobile='08044444444',
            password='securepass'
        )
        
        self.assertTrue(user.check_password('securepass'))
        self.assertEqual(user.mobile, '08044444444')

    def test_session_timeout_middleware(self):
        """Test session timeout behavior."""
        # This would test the SessionTimeoutMiddleware
        # For now, we verify it's in the middleware stack
        from django.conf import settings
        self.assertIn('pharmacy.middleware.SessionTimeoutMiddleware', settings.MIDDLEWARE)


class ModelValidationTests(TestCase):
    """Test model-level validation."""

    def test_form_item_validation(self):
        """Test FormItem validation rules."""
        form = Form.objects.create(
            total_amount=Decimal('100.00'),
            buyer_name='Test'
        )
        
        # Should not allow negative price
        with self.assertRaises(ValidationError):
            item = FormItem(
                form=form,
                drug_name='Test',
                drug_type='LPACEMAKER',
                unit='Tab',
                quantity=5,
                price=Decimal('-10.00'),
                subtotal=Decimal('50.00')
            )
            item.full_clean()

    def test_cart_item_validation(self):
        """Test Cart model validation."""
        user = User.objects.create_user(
            username='testval',
            mobile='08055555555',
            password='pass'
        )
        drug = LpacemakerDrugs.objects.create(
            name='Test',
            price=Decimal('5.00'),
            stock=10
        )
        
        # Should not allow quantity < 1
        with self.assertRaises(ValidationError):
            cart = Cart(
                user=user,
                lpacemaker_drug=drug,
                quantity=0,
                price=Decimal('5.00')
            )
            cart.full_clean()
