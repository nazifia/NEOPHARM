from . models import *
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm, PasswordChangeForm
from .models import LpacemakerDrugs, NcapDrugs, OncologyPharmacy, User, Profile

class LpacemakerDrugsForm(forms.ModelForm):
    class Meta:
        model = LpacemakerDrugs
        fields = ['name', 'dosage_form', 'brand', 'unit', 'price', 'stock', 'exp_date']
        widgets = {
            'exp_date': forms.DateInput(attrs={'type': 'date'}),
        }

class NcapDrugsForm(forms.ModelForm):
    class Meta:
        model = NcapDrugs
        fields = ['name', 'dosage_form', 'brand', 'unit', 'price', 'stock', 'exp_date']
        widgets = {
            'exp_date': forms.DateInput(attrs={'type': 'date'}),
        }

class OncologyPharmacyForm(forms.ModelForm):
    class Meta:
        model = OncologyPharmacy
        fields = ['name', 'dosage_form', 'brand', 'unit', 'price', 'stock', 'exp_date']
        widgets = {
            'exp_date': forms.DateInput(attrs={'type': 'date'}),
        }

class DispenseSearchForm(forms.Form):
    search = forms.CharField(required=False)
    category = forms.ChoiceField(choices=[
        ('all', 'All Categories'),
        ('lpacemaker', 'Lpacemaker Drugs'),
        ('ncap', 'NCAP Drugs'),
        ('oncology', 'Onco-Pharmacy')
    ], required=False)

class EditUserProfileForm(UserChangeForm):

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name']


class addItemForm(forms.ModelForm):
    name = forms.CharField(max_length=200)
    dosage_form = forms.ChoiceField(
        choices=[
            ('Unit', 'Dosage form'),
            ('Tablet', 'Tablet'),
            ('Capsule', 'Capsule'),
            ('Consumable', 'Consumable'),
            ('Cream', 'Cream'),
            ('Syrup', 'Syrup'),
            ('Suspension', 'Suspension'),
            ('Eye-drop', 'Eye-drop'),
            ('Ear-drop', 'Ear-drop'),
            ('Eye-ointment', 'Eye-ointment'),
            ('Nasal', 'Nasal'),
            ('Injection', 'Injection'),
            ('Infusion', 'Infusion'),
            ('Inhaler', 'Inhaler'),
            ('Vaginal', 'Vaginal'),
            ('Rectal', 'Rectal'),
        ],
        widget=forms.Select(attrs={'class': 'form-control mt-3'}),
    )
    brand = forms.CharField(max_length=200)
    unit = forms.CharField(max_length=200)
    cost = forms.DecimalField(max_digits=12, decimal_places=2)
    markup = forms.DecimalField(max_digits=6, decimal_places=2)
    stock = forms.IntegerField()
    exp_date = forms.DateField()

    class Meta:
        model = LpacemakerDrugs
        fields = ('name', 'dosage_form', 'brand', 'unit', 'cost', 'markup', 'stock', 'exp_date')



class dispenseForm(forms.Form):
    q = forms.CharField(min_length=2, label='', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'SEARCH  HERE...'}))



class AddFundsForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2)



class ReturnItemForm(forms.Form):
    return_quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter quantity to return'
        })
    )
    drug_type = forms.CharField(widget=forms.HiddenInput())
    drug_id = forms.IntegerField(widget=forms.HiddenInput())
    return_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control mb-3', 'rows': 3}),
        required=True,
        label="Reason for Return"
    )

    def clean_return_quantity(self):
        quantity = self.cleaned_data.get('return_quantity')
        if quantity <= 0:
            raise forms.ValidationError("Return quantity must be greater than zero.")
        return quantity

class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(max_length=200, required=True)
    mobile = forms.CharField(max_length=20, required=True)
    is_staff = forms.BooleanField(required=False, label='Staff Status')

    class Meta:
        model = User
        fields = ('username', 'mobile', 'password1', 'password2', 'is_staff')

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if User.objects.filter(mobile=mobile).exists():
            raise forms.ValidationError("This mobile number is already registered.")
        return mobile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'mobile']


class EditFormForm(forms.ModelForm):
    class Meta:
        model = Form
        fields = ['buyer_name', 'hospital_no', 'ncap_no']
        widgets = {
            'buyer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'hospital_no': forms.TextInput(attrs={'class': 'form-control'}),
            'ncap_no': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FormItemForm(forms.ModelForm):
    class Meta:
        model = FormItem
        fields = ['drug_name', 'drug_brand', 'drug_type', 'unit', 'quantity', 'price']
        widgets = {
            'drug_name': forms.TextInput(attrs={'class': 'form-control'}),
            'drug_brand': forms.TextInput(attrs={'class': 'form-control'}),
            'drug_type': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('LPACEMAKER', 'LPACEMAKER'),
                ('NCAP', 'NCAP'),
                ('ONCOLOGY', 'ONCO-PHARMACY'),
            ]),
            'unit': forms.Select(attrs={'class': 'form-control'}, choices=UNIT),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        price = cleaned_data.get('price')

        if quantity and price:
            # Calculate subtotal
            cleaned_data['subtotal'] = quantity * price

        return cleaned_data

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'user_type']

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class UserPermissionForm(forms.ModelForm):
    """Form for managing user permissions and groups"""
    groups = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '8'}),
        label='Groups'
    )
    
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '8'}),
        label='Permissions'
    )

    class Meta:
        model = User
        fields = ['username', 'mobile', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType
        
        self.fields['groups'].queryset = Group.objects.all()
        self.fields['user_permissions'].queryset = Permission.objects.filter(
            content_type__app_label__in=['pharmacy', 'auth', 'admin']
        ).order_by('content_type__model', 'codename')


class UserManageForm(forms.ModelForm):
    """Form for creating/editing users with role management"""
    user_type = forms.ChoiceField(
        choices=USER_TYPE,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Role'
    )
    
    full_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Full Name'
    )

    class Meta:
        model = User
        fields = ['username', 'mobile', 'password', 'is_active', 'is_staff', 'is_superuser']
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Editing existing user - populate profile data
            try:
                profile = self.instance.profile
                self.fields['user_type'].initial = profile.user_type
                self.fields['full_name'].initial = profile.full_name
            except Profile.DoesNotExist:
                pass
            # Don't require password for editing
            self.fields['password'].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        
        if commit:
            user.save()
            # Save profile information
            profile, created = Profile.objects.get_or_create(user=user)
            profile.user_type = self.cleaned_data.get('user_type')
            profile.full_name = self.cleaned_data.get('full_name')
            profile.save()
        
        return user


class GroupManageForm(forms.ModelForm):
    """Form for creating/editing groups"""
    permissions = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
        label='Permissions'
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.contenttypes.models import ContentType
        
        self.fields['permissions'].queryset = Permission.objects.filter(
            content_type__app_label__in=['pharmacy', 'auth', 'admin']
        ).order_by('content_type__model', 'codename')


class BulkPermissionActionForm(forms.Form):
    """Form for bulk permission actions"""
    ACTION_CHOICES = [
        ('assign', 'Assign Permission'),
        ('remove', 'Remove Permission'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Action'
    )
    
    permission = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Permission'
    )
    
    user_ids = forms.Field(
        widget=forms.MultipleHiddenInput(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.contenttypes.models import ContentType
        
        self.fields['permission'].queryset = Permission.objects.filter(
            content_type__app_label__in=['pharmacy', 'auth', 'admin']
        ).order_by('content_type__model', 'codename')
