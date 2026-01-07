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
    FormItem
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

# Create your views here.
def is_admin(user):
    return user.is_authenticated and user.is_superuser or user.is_staff

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

def register_user(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to register users.')
        return redirect('store:dashboard')
    
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
    
    context = {
        'lpacemaker_count': lpacemaker_count,
        'ncap_count': ncap_count,
        'oncology_count': oncology_count,
        'cart_count': cart_count,
        'recent_forms': recent_forms,
    }
    
    return render(request, 'store/dashboard.html', context)

def store(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    lpacemaker = LpacemakerDrugs.objects.all().order_by('name')
    ncap = NcapDrugs.objects.all().order_by('name')
    oncology = OncologyPharmacy.objects.all().order_by('name')
    
    context = {
        'lpacemaker': lpacemaker,
        'ncap': ncap,
        'oncology': oncology,
    }
    
    return render(request, 'store/store.html', context)

def add_item(request):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    if request.method == 'POST':
        category = request.POST.get('category')
        name = request.POST.get('name')
        dosage_form = request.POST.get('dosage_form')
        brand = request.POST.get('brand')
        unit = request.POST.get('unit')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        exp_date = request.POST.get('exp_date')
        
        if category == 'lpacemaker':
            LpacemakerDrugs.objects.create(
                name=name,
                dosage_form=dosage_form,
                brand=brand,
                unit=unit,
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
                price=price,
                stock=stock,
                exp_date=exp_date
            )
        
        messages.success(request, 'Item added successfully!')
        return redirect('store:store')
    
    return render(request, 'store/add_item.html')

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
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    quantity = int(request.GET.get('quantity', 1))
    
    if drug_type == 'lpacemaker':
        drug = get_object_or_404(LpacemakerDrugs, pk=pk)
        if drug.stock < quantity:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
        
        cart_item = Cart.objects.filter(
            user=request.user, 
            lpacemaker_drug=drug,
            form__isnull=True
        ).first()
        
        if cart_item:
            # Update existing cart item
            new_quantity = cart_item.quantity + quantity
            if drug.stock < new_quantity:
                return JsonResponse({'error': 'Insufficient stock'}, status=400)
            cart_item.quantity = new_quantity
            cart_item.subtotal = cart_item.calculate_subtotal
            cart_item.save()
        else:
            # Create new cart item
            cart_item = Cart.objects.create(
                user=request.user,
                lpacemaker_drug=drug,
                brand=drug.brand,
                unit=drug.unit,
                quantity=quantity,
                price=drug.price,
                subtotal=drug.price * quantity
            )
        
        # Update stock
        drug.stock -= quantity
        drug.save()
        
    elif drug_type == 'ncap':
        drug = get_object_or_404(NcapDrugs, pk=pk)
        if drug.stock < quantity:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
        
        cart_item = Cart.objects.filter(
            user=request.user, 
            ncap_drug=drug,
            form__isnull=True
        ).first()
        
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if drug.stock < new_quantity:
                return JsonResponse({'error': 'Insufficient stock'}, status=400)
            cart_item.quantity = new_quantity
            cart_item.subtotal = cart_item.calculate_subtotal
            cart_item.save()
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                ncap_drug=drug,
                brand=drug.brand,
                unit=drug.unit,
                quantity=quantity,
                price=drug.price,
                subtotal=drug.price * quantity
            )
        
        drug.stock -= quantity
        drug.save()
        
    elif drug_type == 'oncology':
        drug = get_object_or_404(OncologyPharmacy, pk=pk)
        if drug.stock < quantity:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
        
        cart_item = Cart.objects.filter(
            user=request.user, 
            oncology_drug=drug,
            form__isnull=True
        ).first()
        
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if drug.stock < new_quantity:
                return JsonResponse({'error': 'Insufficient stock'}, status=400)
            cart_item.quantity = new_quantity
            cart_item.subtotal = cart_item.calculate_subtotal
            cart_item.save()
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                oncology_drug=drug,
                brand=drug.brand,
                unit=drug.unit,
                quantity=quantity,
                price=drug.price,
                subtotal=drug.price * quantity
            )
        
        drug.stock -= quantity
        drug.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Added {quantity} {drug.name} to cart',
        'cart_count': Cart.objects.filter(user=request.user, form__isnull=True).count()
    })

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
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        cart_item = Cart.objects.get(pk=pk, user=request.user)
        quantity = int(request.GET.get('quantity', 1))
        
        # Get the related drug
        drug = cart_item.get_item
        
        if quantity <= 0:
            cart_item.delete()
            return JsonResponse({'success': True, 'action': 'removed'})
        
        # Check stock availability
        current_cart_items = Cart.objects.filter(
            user=request.user, 
            form__isnull=True
        ).exclude(pk=pk)
        
        # Calculate what stock would be left after this update
        from django.db import Q
        same_drug_other_carts = current_cart_items.filter(
            Q(lpacemaker_drug=drug) | Q(ncap_drug=drug) | Q(oncology_drug=drug)
        )
        
        total_in_carts = sum(item.quantity for item in same_drug_other_carts)
        
        if drug.stock + cart_item.quantity < quantity + total_in_carts:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
        
        # Update quantity and recalculate subtotal
        cart_item.quantity = quantity
        cart_item.subtotal = cart_item.calculate_subtotal
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'subtotal': float(cart_item.subtotal),
            'action': 'updated'
        })
        
    except Cart.DoesNotExist:
        return JsonResponse({'error': 'Cart item not found'}, status=404)

def remove_from_cart(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        cart_item = Cart.objects.get(pk=pk, user=request.user)
        drug = cart_item.get_item
        
        # Restore stock
        if drug:
            drug.stock += cart_item.quantity
            drug.save()
        
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart'
        })
    except Cart.DoesNotExist:
        return JsonResponse({'error': 'Cart item not found'}, status=404)

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
    
    context = {
        'form': form,
        'cart_items': cart_items,
        'total': total,
    }
    
    if request.method == 'POST':
        # Process the dispensing if there are cart items
        if not cart_items.exists():
            messages.error(request, 'No items in cart to dispense!')
            return render(request, 'store/dispense.html', context)
        
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
    
    if drug_type == 'lpacemaker':
        drug = get_object_or_404(LpacemakerDrugs, pk=pk)
    elif drug_type == 'ncap':
        drug = get_object_or_404(NcapDrugs, pk=pk)
    elif drug_type == 'oncology':
        drug = get_object_or_404(OncologyPharmacy, pk=pk)
    else:
        return JsonResponse({'error': 'Invalid drug type'}, status=400)
    
    # Immediately add to cart and redirect to dispense
    quantity = 1
    
    # Reuse add_to_cart logic inline
    if drug_type == 'lpacemaker':
        if drug.stock < quantity:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
        
        cart_item = Cart.objects.filter(
            user=request.user, 
            lpacemaker_drug=drug,
            form__isnull=True
        ).first()
        
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if drug.stock < new_quantity:
                return JsonResponse({'error': 'Insufficient stock'}, status=400)
            cart_item.quantity = new_quantity
            cart_item.subtotal = cart_item.calculate_subtotal
            cart_item.save()
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                lpacemaker_drug=drug,
                brand=drug.brand,
                unit=drug.unit,
                quantity=quantity,
                price=drug.price,
                subtotal=drug.price * quantity
            )
        
        drug.stock -= quantity
        drug.save()
        
    elif drug_type == 'ncap':
        if drug.stock < quantity:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
        
        cart_item = Cart.objects.filter(
            user=request.user, 
            ncap_drug=drug,
            form__isnull=True
        ).first()
        
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if drug.stock < new_quantity:
                return JsonResponse({'error': 'Insufficient stock'}, status=400)
            cart_item.quantity = new_quantity
            cart_item.subtotal = cart_item.calculate_subtotal
            cart_item.save()
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                ncap_drug=drug,
                brand=drug.brand,
                unit=drug.unit,
                quantity=quantity,
                price=drug.price,
                subtotal=drug.price * quantity
            )
        
        drug.stock -= quantity
        drug.save()
        
    elif drug_type == 'oncology':
        if drug.stock < quantity:
            return JsonResponse({'error': 'Insufficient stock'}, status=400)
        
        cart_item = Cart.objects.filter(
            user=request.user, 
            oncology_drug=drug,
            form__isnull=True
        ).first()
        
        if cart_item:
            new_quantity = cart_item.quantity + quantity
            if drug.stock < new_quantity:
                return JsonResponse({'error': 'Insufficient stock'}, status=400)
            cart_item.quantity = new_quantity
            cart_item.subtotal = cart_item.calculate_subtotal
            cart_item.save()
        else:
            cart_item = Cart.objects.create(
                user=request.user,
                oncology_drug=drug,
                brand=drug.brand,
                unit=drug.unit,
                quantity=quantity,
                price=drug.price,
                subtotal=drug.price * quantity
            )
        
        drug.stock -= quantity
        drug.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Quick dispensed {drug.name}',
        'redirect_url': reverse('store:dispense')
    })

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
    form_items = FormItem.objects.filter(form=form)
    
    context = {
        'form': form,
        'form_items': form_items,
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

def return_lpacemaker_item(request, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    drug = get_object_or_404(LpacemakerDrugs, pk=pk)
    
    if request.method == 'POST':
        return_quantity = int(request.POST.get('return_quantity'))
        return_reason = request.POST.get('return_reason')
        
        if return_quantity <= drug.stock:
            drug.stock += return_quantity
            drug.save()
            messages.success(request, f'{drug.name} returned successfully!')
            return redirect('store:store')
        else:
            messages.error(request, 'Invalid return quantity')
    
    return render(request, 'store/return_item_modal.html', {
        'drug': drug,
        'drug_type': 'lpacemaker',
        'pk': pk
    })

def return_ncap_item(request, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    drug = get_object_or_404(NcapDrugs, pk=pk)
    
    if request.method == 'POST':
        return_quantity = int(request.POST.get('return_quantity'))
        return_reason = request.POST.get('return_reason')
        
        if return_quantity <= drug.stock:
            drug.stock += return_quantity
            drug.save()
            messages.success(request, f'{drug.name} returned successfully!')
            return redirect('store:store')
        else:
            messages.error(request, 'Invalid return quantity')
    
    return render(request, 'store/return_item_modal.html', {
        'drug': drug,
        'drug_type': 'ncap',
        'pk': pk
    })

def return_oncology_item(request, pk):
    if not request.user.is_authenticated:
        return redirect('store:index')
    
    drug = get_object_or_404(OncologyPharmacy, pk=pk)
    
    if request.method == 'POST':
        return_quantity = int(request.POST.get('return_quantity'))
        return_reason = request.POST.get('return_reason')
        
        if return_quantity <= drug.stock:
            drug.stock += return_quantity
            drug.save()
            messages.success(request, f'{drug.name} returned successfully!')
            return redirect('store:store')
        else:
            messages.error(request, 'Invalid return quantity')
    
    return render(request, 'store/return_item_modal.html', {
        'drug': drug,
        'drug_type': 'oncology',
        'pk': pk
    })
