from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.timezone import now
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser, Group, Permission
from shortuuid.django_fields import ShortUUIDField
from datetime import datetime
from decimal import Decimal
from django.conf import settings
import json
from django.core.serializers.json import DjangoJSONEncoder


# Create your models here.
DOSAGE_FORM = [
    ('Tablet', 'Tablet'),
    ('Capsule', 'Capsule'),
    ('Cream', 'Cream'),
    ('Consumable', 'Consumable'),
    ('Injection', 'Injection'),
    ('Infusion', 'Infusion'),
    ('Inhaler', 'Inhaler'),
    ('Suspension', 'Suspension'),
    ('Syrup', 'Syrup'),
    ('Eye-drop', 'Eye-drop'),
    ('Ear-drop', 'Ear-drop'),
    ('Eye-ointment', 'Eye-ointment'),
    ('Rectal', 'Rectal'),
    ('Vaginal', 'Vaginal'),
]


UNIT = [
    ('Amp', 'Amp'),
    ('Bottle', 'Bottle'),
    ('Tab', 'Tab'),
    ('Tin', 'Tin'),
    ('Caps', 'Caps'),
    ('Card', 'Card'),
    ('Carton', 'Carton'),
    ('Pack', 'Pack'),
    ('Packet', 'Packet'),
    ('Pcs', 'Pieces'),
    ('Pieces', 'Pieces'),
    ('Roll', 'Roll'),
    ('Vail', 'Vail'),
    ('1L', '1L'),
    ('2L', '2L'),
    ('4L', '4L'),
]


USER_TYPE = [
    ('Admin', 'Admin'),
    ('Pharmacist', 'Pharmacist'),
    ('Pharm-Tech', 'Pharm-Tech'),
]

# Create your models here.
class User(AbstractUser):
    groups = models.ManyToManyField(Group, related_name="pharmacy_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="pharmacy_user_permissions", blank=True)
    username = models.CharField(max_length=200, null=True, blank=True)
    mobile = models.CharField(max_length=20, unique=True)

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username if self.username else self.mobile

    @property
    def pending_cart_count(self):
        """Get count of items in cart that are not yet part of a form"""
        from django.db.models import Q
        return self.cart_items.filter(form__isnull=True).count()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # image = models.ImageField(upload_to='uploads/images/', blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    user_type = models.CharField(max_length=200, choices=USER_TYPE, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} {self.user_type}'


MARKUP_CHOICES = [
    ('5', '5%'),
    ('10', '10%'),
    ('15', '15%'),
    ('20', '20%'),
    ('25', '25%'),
    ('30', '30%'),
    ('35', '35%'),
    ('40', '40%'),
    ('45', '45%'),
    ('50', '50%'),
    ('55', '55%'),
    ('60', '60%'),
    ('65', '65%'),
    ('70', '70%'),
    ('75', '75%'),
    ('80', '80%'),
    ('85', '85%'),
    ('90', '90%'),
    ('100', '100%'),
]


class LpacemakerDrugs(models.Model):
    name = models.CharField(max_length=200)
    dosage_form = models.CharField(max_length=200, choices=DOSAGE_FORM, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    markup = models.CharField(max_length=10, choices=MARKUP_CHOICES, default='10')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0, null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        # Check if item has expired and zero out stock if so
        if self.exp_date and self.exp_date < timezone.now().date():
            self.stock = 0
        
        # Auto-calculate price if cost and markup are set
        if self.cost and self.markup:
            try:
                markup_percent = float(self.markup)
                self.price = self.cost * (1 + (markup_percent / 100))
            except (ValueError, TypeError):
                pass
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if the item has expired based on exp_date"""
        if not self.exp_date:
            return False
        return self.exp_date < timezone.now().date()

    def get_expiration_status(self):
        """Return expiration status as a string"""
        if not self.exp_date:
            return "No expiry date"
        
        if self.is_expired():
            return f"Expired on {self.exp_date}"
        
        days_remaining = (self.exp_date - timezone.now().date()).days
        if days_remaining <= 7:
            return f"Expires soon ({days_remaining} days)"
        return f"Valid until {self.exp_date}"

    def __str__(self):
        return f'{self.name} {self.brand} {self.unit} {self.price} {self.stock} {self.exp_date}'


class NcapDrugs(models.Model):
    name = models.CharField(max_length=200)
    dosage_form = models.CharField(max_length=200, choices=DOSAGE_FORM, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    markup = models.CharField(max_length=10, choices=MARKUP_CHOICES, default='10')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0, null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        # Check if item has expired and zero out stock if so
        if self.exp_date and self.exp_date < timezone.now().date():
            self.stock = 0
        
        # Auto-calculate price if cost and markup are set
        if self.cost and self.markup:
            try:
                markup_percent = float(self.markup)
                self.price = self.cost * (1 + (markup_percent / 100))
            except (ValueError, TypeError):
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} {self.brand} {self.unit} {self.price} {self.stock} {self.exp_date}'


class OncologyPharmacy(models.Model):
    name = models.CharField(max_length=200)
    dosage_form = models.CharField(max_length=200, choices=DOSAGE_FORM, blank=True, null=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    markup = models.CharField(max_length=10, choices=MARKUP_CHOICES, default='10')
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0, null=True, blank=True)
    exp_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        # Check if item has expired and zero out stock if so
        if self.exp_date and self.exp_date < timezone.now().date():
            self.stock = 0
        
        # Auto-calculate price if cost and markup are set
        if self.cost and self.markup:
            try:
                markup_percent = float(self.markup)
                self.price = self.cost * (1 + (markup_percent / 100))
            except (ValueError, TypeError):
                pass
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if the item has expired based on exp_date"""
        if not self.exp_date:
            return False
        return self.exp_date < timezone.now().date()

    def get_expiration_status(self):
        """Return expiration status as a string"""
        if not self.exp_date:
            return "No expiry date"
        
        if self.is_expired():
            return f"Expired on {self.exp_date}"
        
        days_remaining = (self.exp_date - timezone.now().date()).days
        if days_remaining <= 7:
            return f"Expires soon ({days_remaining} days)"
        return f"Valid until {self.exp_date}"

    def __str__(self):
        return f'{self.name} {self.brand} {self.unit} {self.price} {self.stock} {self.exp_date}'


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cart_items')
    form = models.ForeignKey('Form', on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    lpacemaker_drug = models.ForeignKey(LpacemakerDrugs, on_delete=models.CASCADE, null=True, blank=True)
    ncap_drug = models.ForeignKey(NcapDrugs, on_delete=models.CASCADE, null=True, blank=True)
    oncology_drug = models.ForeignKey(OncologyPharmacy, on_delete=models.CASCADE, null=True, blank=True)
    brand = models.CharField(max_length=200, blank=True, null=True)
    dosage_form = models.CharField(max_length=200, choices=DOSAGE_FORM, blank=True, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cart_id = ShortUUIDField(unique=True, length=5, max_length=50, prefix='CID: ', alphabet='1234567890')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.cart_id} {self.user}'

    @property
    def get_item(self):
        """Returns the active drug item"""
        return self.lpacemaker_drug or self.ncap_drug or self.oncology_drug

    @property
    def calculate_subtotal(self):
        item = self.get_item
        if item:
            return item.price * self.quantity
        return Decimal('0')

    def save(self, *args, **kwargs):
        self.subtotal = self.calculate_subtotal
        super().save(*args, **kwargs)

    def get_drug_type(self):
        """Returns the type of drug in the cart item"""
        if self.lpacemaker_drug:
            return 'lpacemaker'
        elif self.ncap_drug:
            return 'ncap'
        elif self.oncology_drug:
            return 'oncology'
        return None


class Form(models.Model):
    form_id = ShortUUIDField(
        length=5,
        max_length=50,
        prefix="F",
        alphabet="0123456789",
        unique=True
    )
    buyer_name = models.CharField(max_length=255, null=True, blank=True)
    hospital_no = models.CharField(max_length=100, null=True, blank=True)
    ncap_no = models.CharField(max_length=100, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'pharmacy_form'

    def __str__(self):
        return f"Form {self.form_id} - {self.buyer_name}"


class FormItem(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='items')
    drug_name = models.CharField(max_length=255)
    drug_brand = models.CharField(max_length=255, null=True, blank=True)
    drug_type = models.CharField(max_length=50)  # LPACEMAKER, NCAP, ONCOLOGY
    dosage_form = models.CharField(max_length=200, choices=DOSAGE_FORM, blank=True, null=True)
    unit = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.drug_name} - {self.form.form_id}"


class OfflineTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('ADD_TO_CART', 'Add to Cart'),
        ('REMOVE_FROM_CART', 'Remove from Cart'),
        ('CHECKOUT', 'Checkout'),
    )

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    data = models.JSONField(encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(auto_now_add=True)
    synced = models.BooleanField(default=False)
    retry_count = models.IntegerField(default=0)
    version = models.IntegerField(default=1)

    class Meta:
        ordering = ['created_at']

    def process(self):
        if self.transaction_type == 'ADD_TO_CART':
            cart = Cart.objects.get(user=self.data['user_id'])
            # Process add to cart logic
            pass
        elif self.transaction_type == 'CHECKOUT':
            # Process checkout logic
            pass
