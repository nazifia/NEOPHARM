#!/usr/bin/env python
import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from pharmacy import views

# Setup Django
sys.path.append('neopharm/neopharm')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neopharm.settings')
django.setup()

print("=== Testing Search Views Directly ===")

# Create a request factory
factory = RequestFactory()

# Test search_items view
print("\n1. Testing search_items view:")

# Create a mock request
request = factory.get('/search-items/?q=Doxorubicin')
request.user = AnonymousUser()  # Set as anonymous user to see the redirect

try:
    response = views.search_items(request)
    print(f"Response status: {response.status_code}")
    print(f"Response type: {type(response)}")
    if hasattr(response, 'url'):
        print(f"Redirect URL: {response.url}")
except Exception as e:
    print(f"Error: {e}")

# Test get_category_drugs view
print("\n2. Testing get_category_drugs view:")

request = factory.get('/get-category-drugs/?category=lpacemaker')
request.user = AnonymousUser()

try:
    response = views.get_category_drugs(request)
    print(f"Response status: {response.status_code}")
    print(f"Response type: {type(response)}")
    if hasattr(response, 'url'):
        print(f"Redirect URL: {response.url}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== View Test Complete ===")