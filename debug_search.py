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

def test_search_functionality():
    # Create a test client
    client = Client()

    # Get the User model
    User = get_user_model()

    # Try to get the superuser
    try:
        user = User.objects.get(is_superuser=True)
        print(f"Found superuser: {user.username} - {user.mobile}")

        # Login the user
        login_successful = client.login(mobile=user.mobile, password='password')
        if not login_successful:
            print("Failed to login with default password, trying to set password...")

            # Try to set a password if not set
            if not user.has_usable_password():
                user.set_password('password')
                user.save()
                print("Set default password for user")

                # Try login again
                login_successful = client.login(mobile=user.mobile, password='password')

        if login_successful:
            print("Successfully logged in!")

            # Test search endpoints
            print("\n=== Testing Search Endpoints ===")

            # Test 1: Search for "Doxorubicin"
            print("\n1. Testing search for 'Doxorubicin':")
            response = client.get('/search-items/', {'q': 'Doxorubicin'})
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Found {len(data)} results:")
                    for item in data:
                        print(f"  - {item.get('name', 'N/A')} ({item.get('brand', 'N/A')}) - {item.get('type', 'N/A')} - ₦{item.get('price', 'N/A')}")
                except:
                    print(f"Response content: {response.content[:200]}...")
            else:
                print(f"Error response: {response.content[:200]}...")

            # Test 2: Get LPACEMAKER category
            print("\n2. Testing LPACEMAKER category:")
            response = client.get('/get-category-drugs/', {'category': 'lpacemaker'})
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Found {len(data)} results:")
                    for item in data:
                        print(f"  - {item.get('name', 'N/A')} ({item.get('brand', 'N/A')}) - {item.get('type', 'N/A')} - ₦{item.get('price', 'N/A')}")
                except:
                    print(f"Response content: {response.content[:200]}...")
            else:
                print(f"Error response: {response.content[:200]}...")

            return True
        else:
            print("Failed to login. Please check user credentials.")
            return False

    except User.DoesNotExist:
        print("No superuser found. Please create a superuser first:")
        print("python manage.py createsuperuser")
        return False

if __name__ == "__main__":
    test_search_functionality()