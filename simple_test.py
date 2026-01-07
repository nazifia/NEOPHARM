#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append('neopharm/neopharm')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neopharm.settings')
django.setup()

print("Django setup complete")

# Test database queries
from pharmacy.models import LpacemakerDrugs, NcapDrugs, OncologyPharmacy

print("\n=== Testing Database Queries ===")

# Test LPACEMAKER drugs
lpacemaker_drugs = LpacemakerDrugs.objects.all()
print(f"LPACEMAKER drugs count: {lpacemaker_drugs.count()}")
for drug in lpacemaker_drugs:
    print(f"  - {drug.name} - {drug.brand} - {drug.price} - {drug.unit}")

# Test NCAP drugs
ncap_drugs = NcapDrugs.objects.all()
print(f"\nNCAP drugs count: {ncap_drugs.count()}")
for drug in ncap_drugs:
    print(f"  - {drug.name} - {drug.brand} - {drug.price} - {drug.unit}")

# Test ONCOLOGY drugs
oncology_drugs = OncologyPharmacy.objects.all()
print(f"\nONCOLOGY drugs count: {oncology_drugs.count()}")
for drug in oncology_drugs:
    print(f"  - {drug.name} - {drug.brand} - {drug.price} - {drug.unit}")

print("\n=== Database Test Complete ===")