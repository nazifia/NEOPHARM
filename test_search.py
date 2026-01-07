#!/usr/bin/env python
import os
import sys
import django
from django.test import Client
from django.contrib.auth import get_user_model

# Add the project directory to the Python path
sys.path.append('neopharm/neopharm')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neopharm.settings')

# Setup Django
django.setup()

# Create a test client
client = Client()

# Get the User model
User = get_user_model()

# Try to get or create a test user
try:
    user = User.objects.get(mobile='admin')
    print(f"Using existing user: {user}")
except User.DoesNotExist:
    print("No existing user found. Please create a user first.")
    sys.exit(1)

# Login the user
login_successful = client.login(mobile='admin', password='password')
if not login_successful:
    print("Failed to login. Please check credentials.")
    sys.exit(1)

print("Successfully logged in!")

# Test search endpoints
print("\n=== Testing Search Endpoints ===")

# Test 1: Search for "Doxorubicin"
print("\n1. Testing search for 'Doxorubicin':")
response = client.get('/search-items/', {'q': 'Doxorubicin'})
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {len(data)} results:")
    for item in data:
        print(f"  - {item['name']} ({item['brand']}) - {item['type']} - ₦{item['price']}")
else:
    print(f"Error response: {response.content}")

# Test 2: Search for "Paclitaxel"
print("\n2. Testing search for 'Paclitaxel':")
response = client.get('/search-items/', {'q': 'Paclitaxel'})
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {len(data)} results:")
    for item in data:
        print(f"  - {item['name']} ({item['brand']}) - {item['type']} - ₦{item['price']}")
else:
    print(f"Error response: {response.content}")

# Test 3: Get LPACEMAKER category
print("\n3. Testing LPACEMAKER category:")
response = client.get('/get-category-drugs/', {'category': 'lpacemaker'})
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {len(data)} results:")
    for item in data:
        print(f"  - {item['name']} ({item['brand']}) - {item['type']} - ₦{item['price']}")
else:
    print(f"Error response: {response.content}")

# Test 4: Get all categories
print("\n4. Testing all categories:")
response = client.get('/get-category-drugs/', {'category': 'all'})
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {len(data)} results:")
    for item in data:
        print(f"  - {item['name']} ({item['brand']}) - {item['type']} - ₦{item['price']}")
else:
    print(f"Error response: {response.content}")

print("\n=== Test Complete ===")