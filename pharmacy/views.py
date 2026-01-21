from django.db import transaction
from collections import defaultdict
from decimal import Decimal
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.forms import formset_factory
from .models import (
    LpacemakerDrugs,
    NcapDrugs,
    OncologyPharmacy,
    Cart,
    Form,
    FormItem,
    DOSAGE_FORM,
    UNIT,
    Profile
)
from .forms import *
from django.contrib import messages
from django.db import transaction
from datetime import datetime, timedelta
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q, F, ExpressionWrapper, Sum, DecimalField
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db.models.functions import TruncDay
from shortuuid.django_fields import ShortUUIDField
from .forms import UserRegistrationForm
from django.contrib.auth.forms import PasswordChangeForm
from .forms import UserProfileForm, ProfileForm, CustomPasswordChangeForm, EditFormForm, FormItemForm
from .forms import UserPermissionForm, UserManageForm, GroupManageForm, UserCategoryFilterForm, AdminPasswordChangeForm, UserSelfPasswordChangeForm

from .services import DrugService

# Create your views here.
def is_admin(user):
    """Check if user is an Admin based on profile user_type"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.user_type == 'Admin'

def is_superuser_or_staff(user):
    """Check if user is superuser or staff with proper permissions"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)

# Custom decorators for redirect handling
def admin_required(view_func):
    """Decorator that checks if user is an admin and redirects if not"""
    @user_passes_test(is_admin, login_url='store:dashboard', redirect_field_name=None)
    def wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped_view

def superuser_or_staff_required(view_func):
    """Decorator that checks if user is superuser or staff and redirects if not"""
    @user_passes_test(is_superuser_or_staff, login_url='store:dashboard', redirect_field_name=None)
    def wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapped_view

def index(request):

    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('store:dashboard')

    # Handle login form submission
    if request.method == 'POST':
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        next_url = request.POST.get('next') or request.GET.get('next') or 'store:dashboard'

        user = authenticate(request, mobile=mobile, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back!')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid mobile number or password.')

    return render(request, 'store/index.html')

@login_required
@superuser_or_staff_required
def register_user(request):
    """Register new users - now redirects unauthorized users to dashboard"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            messages.success(request, f'User {user.username} registered successfully')
            return redirect('store:dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'store/register.html', {'form': form})

def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('store:index')

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    # Count items in each category
    lpacemaker_count = LpacemakerDrugs.objects.count()
    ncap_count = NcapDrugs.objects.count()
    oncology_count = OncologyPharmacy.objects.count()
    
    # Count cart items for current user
    cart_count = Cart.objects.filter(user=request.user).count()
    
    # Recent forms
    recent_forms = Form.objects.all().order_by('-date')[:5]
    
    # User statistics (for staff/superusers)
    user_stats = {}
    if request.user.is_staff or request.user.is_superuser:
        from django.contrib.auth.models import Group
        
        # User counts by category
        admin_users = User.objects.filter(profile__user_type='Admin').count()
        pharmacist_users = User.objects.filter(profile__user_type='Pharmacist').count()
        tech_users = User.objects.filter(profile__user_type='Pharm-Tech').count()
        total_users = User.objects.count()
        active_staff = User.objects.filter(is_staff=True, is_active=True).count()
        
        user_stats = {
            'admin_users': admin_users,
            'pharmacist_users': pharmacist_users,
            'tech_users': tech_users,
            'total_users': total_users,
            'active_staff': active_staff,
            'total_groups': Group.objects.count(),
        }
    
    context = {
        'lpacemaker_count': lpacemaker_count,
        'ncap_count': ncap_count,
        'oncology_count': oncology_count,
        'cart_count': cart_count,
        'recent_forms': recent_forms,
        'user_stats': user_stats,
    }
    
    return render(request, 'store/dashboard.html', context)

def store(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    lpacemaker = LpacemakerDrugs.objects.all().order_by('name')
    ncap = NcapDrugs.objects.all().order_by('name')
    oncology = OncologyPharmacy.objects.all().order_by('name')
    
    # Calculate statistics for each category
    lpacemaker_stats = {
        'total_items': lpacemaker.count(),
        'total_stock_value': sum(item.price * item.stock for item in lpacemaker),
        'low_stock_items': [item for item in lpacemaker if item.stock < 10]
    }
    
    ncap_stats = {
        'total_items': ncap.count(),
        'total_stock_value': sum(item.price * item.stock for item in ncap),
        'low_stock_items': [item for item in ncap if item.stock < 10]
    }
    
    oncology_stats = {
        'total_items': oncology.count(),
        'total_stock_value': sum(item.price * item.stock for item in oncology),
        'low_stock_items': [item for item in oncology if item.stock < 10]
    }
    
    context = {
        'lpacemaker': lpacemaker,
        'ncap': ncap,
        'oncology': oncology,
        'lpacemaker_stats': lpacemaker_stats,
        'ncap_stats': ncap_stats,
        'oncology_stats': oncology_stats,
    }
    
    return render(request, 'store/store.html', context)

def add_item(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    if request.method == 'POST':
        category = request.POST.get('store_type')  # Fixed field name to match template
        name = request.POST.get('name')
        dosage_form = request.POST.get('dosage_form')
        brand = request.POST.get('brand')
        unit = request.POST.get('unit')
        cost = request.POST.get('cost')
        markup = request.POST.get('markup')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        exp_date = request.POST.get('exp_date')
        
        if category == 'lpacemaker':
            LpacemakerDrugs.objects.create(
                name=name,
                dosage_form=dosage_form,
                brand=brand,
                unit=unit,
                cost=cost,
                markup=markup,
                price=price,
                stock=stock,
                exp_date=exp_date
            )
        elif category == 'ncap':
            NcapDrugs.objects.create(
                name=name,
                dosage_form=dosage_form,
                brand=brand,
                unit=unit,
                cost=cost,
                markup=markup,
                price=price,
                stock=stock,
                exp_date=exp_date
            )
        elif category == 'oncology':
            OncologyPharmacy.objects.create(
                name=name,
                dosage_form=dosage_form,
                brand=brand,
                unit=unit,
                cost=cost,
                markup=markup,
                price=price,
                stock=stock,
                exp_date=exp_date
            )
        
        messages.success(request, 'Item added successfully!')
        return redirect('store:store')
    
    return render(request, 'store/add_item.html', {
        'dosage_forms': DOSAGE_FORM,
        'units': UNIT,
        'markup_choices': [('5', '5%'), ('10', '10%'), ('15', '15%'), ('20', '20%'), ('25', '25%'), ('30', '30%'), ('35', '35%'), ('40', '40%'), ('45', '45%'), ('50', '50%'), ('55', '55%'), ('60', '60%'), ('65', '65%'), ('70', '70%'), ('75', '75%'), ('80', '80%'), ('85', '85%'), ('90', '90%'), ('100', '100%')]
    })

def edit_item(request, drug_type, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    if drug_type == 'lpacemaker':
        item = get_object_or_404(LpacemakerDrugs, pk=pk)
        form_class = LpacemakerDrugsForm
    elif drug_type == 'ncap':
        item = get_object_or_404(NcapDrugs, pk=pk)
        form_class = NcapDrugsForm
    elif drug_type == 'oncology':
        item = get_object_or_404(OncologyPharmacy, pk=pk)
        form_class = OncologyPharmacyForm
    else:
        messages.error(request, 'Invalid drug type')
        return redirect('store:store')
    
    if request.method == 'POST':
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully!')
            return redirect('store:store')
    else:
        form = form_class(instance=item)
    
    return render(request, 'store/edit_item.html', {'form': form, 'item': item, 'drug_type': drug_type})

def delete_item(request, drug_type, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    if drug_type == 'lpacemaker':
        item = get_object_or_404(LpacemakerDrugs, pk=pk)
    elif drug_type == 'ncap':
        item = get_object_or_404(NcapDrugs, pk=pk)
    elif drug_type == 'oncology':
        item = get_object_or_404(OncologyPharmacy, pk=pk)
    else:
        messages.error(request, 'Invalid drug type')
        return redirect('store:store')
    
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully!')
        return redirect('store:store')
    
    return render(request, 'store/delete_item_confirm.html', {'item': item, 'drug_type': drug_type})

def add_to_cart(request, drug_type, pk):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            messages.error(request, 'Not authenticated')
            return redirect('store:index')
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
    else:
        quantity = int(request.GET.get('quantity', 1))
    
    success, message, status = DrugService.add_to_cart(request.user, drug_type, pk, quantity)
    
    if success:
        if request.method == 'POST':
            messages.success(request, message)
            return redirect('store:dispense')
        else:
            return JsonResponse({
                'success': True,
                'message': message,
                'cart_count': Cart.objects.filter(user=request.user, form__isnull=True).count()
            })
    else:
        if request.method == 'POST':
            messages.error(request, message)
            return redirect('store:dispense')
        else:
            return JsonResponse({'error': message}, status=status)

def cart(request):

    if not request.user.is_authenticated:
        return redirect('store:index')
    
    # Get all cart items that are not yet part of a form (pending cart)
    cart_items = Cart.objects.filter(
        user=request.user, 
        form__isnull=True
    ).order_by('-created_at')
    
    # Calculate total
    total = sum(item.subtotal for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
    }
    
    return render(request, 'store/cart.html', context)

def update_cart(request, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    try:
        cart_item = Cart.objects.get(pk=pk, user=request.user)
        
        # Handle form data from POST or query param from GET
        if request.method == 'POST':
            quantity = int(request.POST.get('quantity', 1))
        else:
            quantity = int(request.GET.get('quantity', 1))
        
        # Get the related drug
        drug = cart_item.get_item
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, 'Item removed from cart')
            return redirect('store:cart')
        
        # Check stock availability
        current_cart_items = Cart.objects.filter(
            user=request.user, 
            form__isnull=True
        ).exclude(pk=pk)
        
        # Calculate what stock would be left after this update
        # Use the drug type to filter correctly
        drug_type = cart_item.get_drug_type()
        if drug_type == 'lpacemaker':
            same_drug_other_carts = current_cart_items.filter(lpacemaker_drug=drug)
        elif drug_type == 'ncap':
            same_drug_other_carts = current_cart_items.filter(ncap_drug=drug)
        elif drug_type == 'oncology':
            same_drug_other_carts = current_cart_items.filter(oncology_drug=drug)
        else:
            same_drug_other_carts = current_cart_items.none()
        
        total_in_carts = sum(item.quantity for item in same_drug_other_carts)
        
        if drug.stock + cart_item.quantity < quantity + total_in_carts:
            messages.error(request, 'Insufficient stock')
            return redirect('store:cart')
        
        # Update quantity and recalculate subtotal
        cart_item.quantity = quantity
        cart_item.subtotal = cart_item.calculate_subtotal
        cart_item.save()
        
        messages.success(request, 'Cart updated successfully')
        return redirect('store:cart')
        
    except Cart.DoesNotExist:
        messages.error(request, 'Cart item not found')
        return redirect('store:cart')

def remove_from_cart(request, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    try:
        cart_item = Cart.objects.get(pk=pk, user=request.user)
        drug = cart_item.get_item
        
        # Restore stock
        if drug:
            drug.stock += cart_item.quantity
            drug.save()
        
        cart_item.delete()
        
        messages.success(request, 'Item removed from cart')
        return redirect('store:cart')
    except Cart.DoesNotExist:
        messages.error(request, 'Cart item not found')
        return redirect('store:cart')

def clear_cart(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    cart_items = Cart.objects.filter(user=request.user, form__isnull=True)
    
    # Restore stock for all items
    for item in cart_items:
        drug = item.get_item
        if drug:
            drug.stock += item.quantity
            drug.save()
    
    cart_items.delete()
    messages.success(request, 'Cart cleared successfully!')
    return redirect('store:cart')

def dispense(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    form = dispenseForm()
    
    # Get cart items for the user
    cart_items = Cart.objects.filter(user=request.user, form__isnull=True)
    
    # Calculate total
    total = sum(item.subtotal for item in cart_items)
    
    # Handle search functionality
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    
    results = {
        'lpacemaker_items': [],
        'ncap_items': [],
        'oncology_items': []
    }
    
    # If no query provided, show all items (up to reasonable limit)
    if not query:
        if category in ['all', 'lpacemaker']:
            all_lpacemaker = LpacemakerDrugs.objects.all()[:50]  # Limit for performance
            for drug in all_lpacemaker:
                results['lpacemaker_items'].append({
                    'id': drug.id,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                    'unit': drug.unit,
                })
        
        if category in ['all', 'ncap']:
            all_ncap = NcapDrugs.objects.all()[:50]
            for drug in all_ncap:
                results['ncap_items'].append({
                    'id': drug.id,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                    'unit': drug.unit,
                })
        
        if category in ['all', 'oncology']:
            all_oncology = OncologyPharmacy.objects.all()[:50]
            for drug in all_oncology:
                results['oncology_items'].append({
                    'id': drug.id,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                    'unit': drug.unit,
                })
    else:
        # Search functionality
        if category in ['all', 'lpacemaker']:
            lpacemaker_results = LpacemakerDrugs.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )
            for drug in lpacemaker_results:
                results['lpacemaker_items'].append({
                    'id': drug.id,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                    'unit': drug.unit,
                })
        
        if category in ['all', 'ncap']:
            ncap_results = NcapDrugs.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )
            for drug in ncap_results:
                results['ncap_items'].append({
                    'id': drug.id,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                    'unit': drug.unit,
                })
        
        if category in ['all', 'oncology']:
            oncology_results = OncologyPharmacy.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )
            for drug in oncology_results:
                results['oncology_items'].append({
                    'id': drug.id,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                    'unit': drug.unit,
                })
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total': total,
        'results': results,
        'query': query,
        'category': category,
    }
    
    if request.method == 'POST':
        # Process the dispensing if there are cart items
        if not cart_items.exists():
            messages.error(request, 'No items in cart to dispense!')
            return render(request, 'store/dispense.html', context)
        
        try:
            with transaction.atomic():
                # Create form
                buyer_name = request.POST.get('buyer_name')
                hospital_no = request.POST.get('hospital_no')
                ncap_no = request.POST.get('ncap_no')
                
                form_record = Form.objects.create(
                    buyer_name=buyer_name,
                    hospital_no=hospital_no,
                    ncap_no=ncap_no,
                    total_amount=total,
                    dispensed_by=request.user
                )
                
                # Move cart items to form items
                for cart_item in cart_items:
                    drug = cart_item.get_item
                    
                    FormItem.objects.create(
                        form=form_record,
                        drug_name=drug.name,
                        drug_brand=drug.brand if hasattr(drug, 'brand') else None,
                        drug_type=cart_item.get_drug_type().upper(),
                        dosage_form=drug.dosage_form if hasattr(drug, 'dosage_form') else None,
                        unit=cart_item.unit,
                        quantity=cart_item.quantity,
                        price=cart_item.price,
                        subtotal=cart_item.subtotal
                    )
                    
                    # Link cart item to form
                    cart_item.form = form_record
                    cart_item.save()
            
            messages.success(request, f'Dispensing successful! Form ID: {form_record.form_id}')
            return redirect('store:receipt')
            
        except Exception as e:
            messages.error(request, f'Error dispensing items: {str(e)}')
            return render(request, 'store/dispense.html', context)

    
    return render(request, 'store/dispense.html', context)

def receipt(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    # Get all forms (receipts)
    forms = Form.objects.all().order_by('-date')
    
    return render(request, 'store/receipt.html', {'forms': forms})

def receipt_detail(request, receipt_id):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    form = get_object_or_404(Form, form_id=receipt_id)
    form_items = FormItem.objects.filter(form=form)
    
    context = {
        'form': form,
        'form_items': form_items,
    }
    
    return render(request, 'store/receipt_detail.html', context)

def search_item(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    
    results = []
    
    if query:
        if category in ['all', 'lpacemaker']:
            lpacemaker_results = LpacemakerDrugs.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )
            for drug in lpacemaker_results:
                results.append({
                    'type': 'lpacemaker',
                    'drug': drug,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                })
        
        if category in ['all', 'ncap']:
            ncap_results = NcapDrugs.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )
            for drug in ncap_results:
                results.append({
                    'type': 'ncap',
                    'drug': drug,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                })
        
        if category in ['all', 'oncology']:
            oncology_results = OncologyPharmacy.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )
            for drug in oncology_results:
                results.append({
                    'type': 'oncology',
                    'drug': drug,
                    'name': drug.name,
                    'brand': drug.brand,
                    'price': drug.price,
                    'stock': drug.stock,
                })
    
    return render(request, 'store/dispense.html', {
        'form': dispenseForm(),
        'results': results,
        'query': query,
        'category': category
    })

def quick_dispense(request, drug_type, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    # Reuse add_to_cart logic via service
    success, message, status = DrugService.add_to_cart(request.user, drug_type, pk, quantity=1)
    
    if success:
        return JsonResponse({
            'success': True,
            'message': f'Quick dispensed item',
            'redirect_url': reverse('store:dispense')
        })
    else:
        return JsonResponse({'error': message}, status=status)

def search_items(request):

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    
    results = []
    
    if query:
        if category in ['all', 'lpacemaker']:
            lpacemaker_results = LpacemakerDrugs.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )[:10]
            for drug in lpacemaker_results:
                results.append({
                    'id': drug.id,
                    'type': 'lpacemaker',
                    'name': drug.name,
                    'brand': drug.brand or '',
                    'price': float(drug.price),
                    'stock': drug.stock,
                    'unit': drug.unit
                })
        
        if category in ['all', 'ncap']:
            ncap_results = NcapDrugs.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )[:10]
            for drug in ncap_results:
                results.append({
                    'id': drug.id,
                    'type': 'ncap',
                    'name': drug.name,
                    'brand': drug.brand or '',
                    'price': float(drug.price),
                    'stock': drug.stock,
                    'unit': drug.unit
                })
        
        if category in ['all', 'oncology']:
            oncology_results = OncologyPharmacy.objects.filter(
                Q(name__icontains=query) | Q(brand__icontains=query)
            )[:10]
            for drug in oncology_results:
                results.append({
                    'id': drug.id,
                    'type': 'oncology',
                    'name': drug.name,
                    'brand': drug.brand or '',
                    'price': float(drug.price),
                    'stock': drug.stock,
                    'unit': drug.unit
                })
    
    return JsonResponse({'results': results})

def get_category_drugs(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    category = request.GET.get('category')
    query = request.GET.get('q', '').strip()
    
    drugs = []
    
    if category == 'lpacemaker':
        qs = LpacemakerDrugs.objects.all()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(brand__icontains=query))
        
        for drug in qs[:10]:
            drugs.append({
                'id': drug.id,
                'name': drug.name,
                'brand': drug.brand or '',
                'price': float(drug.price),
                'stock': drug.stock,
                'unit': drug.unit
            })
            
    elif category == 'ncap':
        qs = NcapDrugs.objects.all()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(brand__icontains=query))
        
        for drug in qs[:10]:
            drugs.append({
                'id': drug.id,
                'name': drug.name,
                'brand': drug.brand or '',
                'price': float(drug.price),
                'stock': drug.stock,
                'unit': drug.unit
            })
            
    elif category == 'oncology':
        qs = OncologyPharmacy.objects.all()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(brand__icontains=query))
        
        for drug in qs[:10]:
            drugs.append({
                'id': drug.id,
                'name': drug.name,
                'brand': drug.brand or '',
                'price': float(drug.price),
                'stock': drug.stock,
                'unit': drug.unit
            })
    
    return JsonResponse({'drugs': drugs})

def profile(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    # Get user's profile
    profile = request.user.profile
    
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('store:profile')
    else:
        user_form = UserProfileForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    
    return render(request, 'store/profile.html', context)

def form_list(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    forms = Form.objects.all().order_by('-date')
    
    return render(request, 'store/forms.html', {'forms': forms})

def view_form(request, form_id):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    form = get_object_or_404(Form, form_id=form_id)
    items = FormItem.objects.filter(form=form)
    
    # Calculate category totals
    category_totals = {
        'LPACEMAKER': sum(item.subtotal for item in items if item.drug_type.upper() == 'LPACEMAKER'),
        'NCAP': sum(item.subtotal for item in items if item.drug_type.upper() == 'NCAP'),
        'ONCOLOGY': sum(item.subtotal for item in items if item.drug_type.upper() == 'ONCOLOGY'),
    }
    
    context = {
        'form': form,
        'items': items,
        'category_totals': category_totals,
        'total_amount': form.total_amount,
    }
    
    return render(request, 'store/form_detail.html', context)

def edit_form(request, form_id):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    form_obj = get_object_or_404(Form, form_id=form_id)
    
    if request.method == 'POST':
        form = EditFormForm(request.POST, instance=form_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Form updated successfully!')
            return redirect('store:view_form', form_id=form_id)
    else:
        form = EditFormForm(instance=form_obj)
    
    return render(request, 'store/edit_form.html', {'form': form, 'form_obj': form_obj})

def add_form_item(request, form_id):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    form_obj = get_object_or_404(Form, form_id=form_id)
    
    if request.method == 'POST':
        form = FormItemForm(request.POST)
        if form.is_valid():
            form_item = form.save(commit=False)
            form_item.form = form_obj
            form_item.save()
            
            # Update form total
            form_obj.total_amount = sum(item.subtotal for item in FormItem.objects.filter(form=form_obj))
            form_obj.save()
            
            messages.success(request, 'Form item added successfully!')
            return redirect('store:view_form', form_id=form_id)
    else:
        form = FormItemForm()
    
    return render(request, 'store/edit_form_item.html', {'form': form, 'form_obj': form_obj, 'action': 'Add'})

def edit_form_item(request, form_id, item_id):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    form_obj = get_object_or_404(Form, form_id=form_id)
    form_item = get_object_or_404(FormItem, id=item_id)
    
    if request.method == 'POST':
        form = FormItemForm(request.POST, instance=form_item)
        if form.is_valid():
            form.save()
            
            # Update form total
            form_obj.total_amount = sum(item.subtotal for item in FormItem.objects.filter(form=form_obj))
            form_obj.save()
            
            messages.success(request, 'Form item updated successfully!')
            return redirect('store:view_form', form_id=form_id)
    else:
        form = FormItemForm(instance=form_item)
    
    return render(request, 'store/edit_form_item.html', {'form': form, 'form_obj': form_obj, 'action': 'Edit'})

def remove_form_item(request, form_id, item_id):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    form_obj = get_object_or_404(Form, form_id=form_id)
    form_item = get_object_or_404(FormItem, id=item_id)
    
    form_item.delete()
    
    # Update form total
    form_obj.total_amount = sum(item.subtotal for item in FormItem.objects.filter(form=form_obj))
    form_obj.save()
    
    messages.success(request, 'Form item removed successfully!')
    return redirect('store:view_form', form_id=form_id)

def return_item(request, drug_type, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    try:
        drug = DrugService.get_drug(drug_type, pk)
    except ValueError:
        return redirect('store:store')
    
    if request.method == 'POST':
        try:
            return_quantity = int(request.POST.get('return_quantity', 0))
            
            if return_quantity <= 0:
                messages.error(request, 'Invalid return quantity')
            else:
                success, message = DrugService.return_item(drug_type, pk, return_quantity)
                if success:
                    messages.success(request, message)
                    return redirect('store:store')
                else:
                    messages.error(request, message)
        except ValueError:
             messages.error(request, 'Invalid quantity')
    
    return render(request, 'store/return_item_modal.html', {
        'drug': drug,
        'drug_type': drug_type,
        'pk': pk
    })


# ========== ADMIN USER & PERMISSION MANAGEMENT VIEWS ==========

@login_required
@user_passes_test(is_admin)
def admin_users_list(request, category=None):
    """Admin view to list all users with filtering and categories"""
    # Get all users for stats
    all_users = User.objects.all()
    
    # Handle filtering from GET params or URL parameter
    filter_category = request.GET.get('category', category or '')
    status = request.GET.get('status', 'all')
    
    # Filter by category
    users = User.objects.all()
    if filter_category:
        users = users.filter(profile__user_type=filter_category)
    
    # Filter by status
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    elif status == 'staff':
        users = users.filter(is_staff=True)
    
    users = users.order_by('-date_joined')
    
    # Calculate statistics
    total_users = all_users.count()
    user_stats = {}
    
    for user_type in ['Admin', 'Pharmacist', 'Pharm-Tech']:
        user_stats[user_type] = {
            'count': all_users.filter(profile__user_type=user_type).count(),
            'active': all_users.filter(profile__user_type=user_type, is_active=True).count(),
        }
    
    # Group users by category
    users_by_category = {}
    for user in users:
        category_name = user.profile.user_type or 'Unassigned'
        if category_name not in users_by_category:
            users_by_category[category_name] = []
        users_by_category[category_name].append(user)
    
    # Initialize form
    filter_form = UserCategoryFilterForm(initial={
        'category': filter_category,
        'status': status,
    })
    
    context = {
        'users': users,
        'users_by_category': users_by_category,
        'filter_form': filter_form,
        'total_users': total_users,
        'user_stats': user_stats,
        'selected_category': filter_category,
        'selected_status': status,
    }
    return render(request, 'store/admin/users_list.html', context)


@login_required
@user_passes_test(is_admin)
def admin_user_create(request):
    """Admin view to create a new user"""
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can create new users.')
        return redirect('store:admin_users_list')
    
    if request.method == 'POST':
        form = UserManageForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully!')
            return redirect('store:admin_users_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserManageForm()
    
    return render(request, 'store/admin/user_form.html', {
        'form': form,
        'title': 'Create New User',
        'action': 'create'
    })


@login_required
@user_passes_test(is_admin)
def admin_user_edit(request, user_id):
    """Admin view to edit a user"""
    user = get_object_or_404(User, id=user_id)
    
    if not request.user.is_superuser and user != request.user:
        messages.error(request, 'You can only edit your own profile.')
        return redirect('store:admin_users_list')
    
    if request.method == 'POST':
        form = UserManageForm(request.POST, instance=user)
        if form.is_valid():
            updated_user = form.save()
            messages.success(request, f'User "{updated_user.username}" updated successfully!')
            return redirect('store:admin_users_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserManageForm(instance=user)
    
    return render(request, 'store/admin/user_form.html', {
        'form': form,
        'title': f'Edit User: {user.username}',
        'action': 'edit',
        'user': user
    })


@login_required
@user_passes_test(is_admin)
def admin_user_delete(request, user_id):
    """Admin view to delete a user"""
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can delete users.')
        return redirect('store:admin_users_list')
    
    user = get_object_or_404(User, id=user_id)
    
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('store:admin_users_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully!')
        return redirect('store:admin_users_list')
    
    return render(request, 'store/admin/user_delete_confirm.html', {
        'user': user
    })


@login_required
@user_passes_test(is_admin)
def admin_user_permissions(request, user_id):
    """Admin view to manage a user's permissions and groups"""
    user = get_object_or_404(User, id=user_id)
    
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can manage user permissions.')
        return redirect('store:admin_users_list')
    
    if request.method == 'POST':
        form = UserPermissionForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Permissions updated for user "{user.username}"!')
            return redirect('store:admin_user_permissions', user_id=user.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserPermissionForm(instance=user)
    
    # Get user's current permissions for display
    user_perms = user.user_permissions.all().order_by('content_type__model', 'codename')
    user_groups = user.groups.all()
    
    return render(request, 'store/admin/user_permissions.html', {
        'form': form,
        'user': user,
        'user_perms': user_perms,
        'user_groups': user_groups,
        'title': f'Manage Permissions: {user.username}'
    })


@login_required
@user_passes_test(is_admin)
def admin_groups_list(request):
    """Admin view to list all groups"""
    from django.contrib.auth.models import Group
    groups = Group.objects.all().order_by('name')
    
    context = {
        'groups': groups,
    }
    return render(request, 'store/admin/groups_list.html', context)


@login_required
@user_passes_test(is_admin)
def admin_group_create(request):
    """Admin view to create a new group"""
    from django.contrib.auth.models import Group
    
    if request.method == 'POST':
        form = GroupManageForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Group "{group.name}" created successfully!')
            return redirect('store:admin_groups_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = GroupManageForm()
    
    return render(request, 'store/admin/group_form.html', {
        'form': form,
        'title': 'Create New Group',
        'action': 'create'
    })


@login_required
@user_passes_test(is_admin)
def admin_group_edit(request, group_id):
    """Admin view to edit a group"""
    from django.contrib.auth.models import Group
    
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        form = GroupManageForm(request.POST, instance=group)
        if form.is_valid():
            updated_group = form.save()
            messages.success(request, f'Group "{updated_group.name}" updated successfully!')
            return redirect('store:admin_groups_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = GroupManageForm(instance=group)
    
    return render(request, 'store/admin/group_form.html', {
        'form': form,
        'title': f'Edit Group: {group.name}',
        'action': 'edit',
        'group': group
    })


@login_required
@user_passes_test(is_admin)
def admin_group_delete(request, group_id):
    """Admin view to delete a group"""
    from django.contrib.auth.models import Group
    
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f'Group "{group_name}" deleted successfully!')
        return redirect('store:admin_groups_list')
    
    return render(request, 'store/admin/group_delete_confirm.html', {
        'group': group
    })


@login_required
@user_passes_test(is_admin)
def admin_group_view(request, group_id):
    """Admin view to view a group's members and permissions"""
    from django.contrib.auth.models import Group
    
    group = get_object_or_404(Group, id=group_id)
    group_permissions = group.permissions.all().order_by('content_type__model', 'codename')
    group_members = group.user_set.all().order_by('username')
    
    context = {
        'group': group,
        'group_permissions': group_permissions,
        'group_members': group_members,
    }
    return render(request, 'store/admin/group_detail.html', context)


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard showing user statistics"""
    from django.contrib.auth.models import Group
    
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()
    superusers = User.objects.filter(is_superuser=True).count()
    total_groups = Group.objects.count()
    
    recent_users = User.objects.order_by('-date_joined')[:5]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,
        'superusers': superusers,
        'total_groups': total_groups,
        'recent_users': recent_users,
    }
    
    return render(request, 'store/admin/dashboard.html', context)


# ========== PASSWORD MANAGEMENT VIEWS ==========

@login_required
@user_passes_test(is_superuser_or_staff)
def admin_user_change_password(request, user_id):
    """Admin view to change any user's password"""
    user = get_object_or_404(User, id=user_id)
    
    # Only superusers can change other users' passwords
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can change user passwords.')
        return redirect('store:admin_users_list')
    
    # Prevent changing own password through this form (use profile for that)
    if user == request.user:
        messages.info(request, 'Please use your profile page to change your own password.')
        return redirect('store:profile')
    
    if request.method == 'POST':
        form = AdminPasswordChangeForm(request.POST)
        if form.is_valid():
            # Set new password
            user.set_password(form.cleaned_data['new_password'])
            
            # Force logout if requested
            if form.cleaned_data['force_logout']:
                # Invalidate all sessions (jwt logout or force re-authentication)
                # In Django, changing password normally invalidates sessions, but we can reinforce it
                user.save()  # Save to ensure password is updated
                messages.warning(request, f'User "{user.username}" logged out of all sessions.')
            
            user.save()
            messages.success(request, f'Password changed successfully for user "{user.username}"')
            
            # Log the action
            messages.info(request, f'New password: {form.cleaned_data["new_password"]} (share securely)')
            
            return redirect('store:admin_users_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AdminPasswordChangeForm()
    
    return render(request, 'store/admin/user_change_password.html', {
        'form': form,
        'user': user,
        'title': f'Change Password: {user.username}'
    })


@login_required
def profile_change_password(request):
    """View for users to change their own password from profile"""
    if request.method == 'POST':
        form = UserSelfPasswordChangeForm(request.POST, user=request.user)
        if form.is_valid():
            # Change password
            request.user.set_password(form.cleaned_data['new_password'])
            request.user.save()
            
            messages.success(request, 'Your password has been changed successfully!')
            messages.info(request, 'Please log in again with your new password.')
            
            return redirect('store:logout_user')
    else:
        form = UserSelfPasswordChangeForm(user=request.user)
    
    return render(request, 'store/profile_change_password.html', {
        'form': form,
        'title': 'Change Your Password'
    })


@login_required
@superuser_or_staff_required
def admin_profile_password_change(request, user_id):
    """Admin view to set a new password for a user (no current password needed)"""
    user = get_object_or_404(User, id=user_id)
    
    if not request.user.is_superuser:
        messages.error(request, 'Only superusers can set user passwords directly.')
        return redirect('store:admin_users_list')
    
    if user == request.user:
        return redirect('store:profile')
    
    if request.method == 'POST':
        form = AdminPasswordChangeForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password'])
            user.save()
            
            messages.success(request, f'Password set successfully for "{user.username}"')
            
            if form.cleaned_data['force_logout']:
                messages.info(request, f'User "{user.username}" must login with new password')
            
            return redirect('store:admin_user_permissions', user_id=user.id)
    else:
        form = AdminPasswordChangeForm()
    
    return render(request, 'store/admin/user_change_password.html', {
        'form': form,
        'user': user,
        'title': f'Set New Password: {user.username}',
        'is_set': True
    })

