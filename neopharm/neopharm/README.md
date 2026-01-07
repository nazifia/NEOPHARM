# NEOPHARM Pharmacy Management System

## Overview
A Django-based pharmacy management system for handling drug inventory, dispensing, and receipt generation. This project has been significantly improved with security enhancements, better architecture, and proper error handling.

## Key Improvements Applied

### 1. Security Hardening
- **Environment Variables**: Moved secrets from code to `.env` file
- **Production-ready Settings**: Added security headers and SSL support
- **CSRF Protection**: Added `@csrf_protect` to all sensitive operations
- **Input Validation**: Comprehensive model-level validation for all critical fields

### 2. Architecture Improvements
- **Service Layer**: Created `services.py` with `DrugService`, `CartService`, `FormService`, and `ReportingService`
- **Reduced Code Duplication**: Consolidated repeated drug type handling logic
- **Database Indexes**: Added indexes on frequently queried fields (name, stock, price, exp_date)
- **Transaction Management**: Proper atomic transactions for all critical operations

### 3. Code Quality
- **Validation**: Added `clean()` methods to all models for data integrity
- **Logging**: Comprehensive logging throughout the application
- **Error Handling**: Proper exception handling with user-friendly messages
- **Documentation**: Added docstrings to all major functions

### 4. Testing
- **Comprehensive Test Suite**: 4 test classes with 20+ test methods
- **Model Tests**: Validate business rules and constraints
- **Service Tests**: Test service layer functionality
- **Security Tests**: Verify authentication and authorization

### 5. Performance
- **Optimized Queries**: Use of `select_related()` and `prefetch_related()`
- **Stock Operations**: Atomic updates with `select_for_update()` to prevent race conditions
- **Caching Structure**: Ready for easy caching implementation
- **Index Database**: New database indexes for faster lookups

## Files Created/Modified

### New Files
- `services.py` - Service layer for business logic
- `tests.py` - Comprehensive test suite
- `.env.example` - Environment variable template
- `README.md` - This documentation

### Modified Files
- `models.py` - Added validation, indexes, and properties
- `views.py` - Added error handling, logging, CSRF protection
- `settings.py` - Environment-based configuration, security settings, logging

### New Migrations
- `0009_add_database_indexes.py` - Database optimization

## Installation & Setup

### 1. Setup Environment
```bash
cd "C:\Users\Dell\Desktop\NEOPHARM\neopharm\neopharm"
copy .env.example .env
```

### 2. Configure Environment Variables
Edit `.env` file:
```env
DJANGO_SECRET_KEY=your-actual-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. Install Dependencies
The dependencies in `requirements.txt` are already installed.

### 4. Apply Migrations
```bash
python manage.py migrate
```

### 5. Run Tests
```bash
python manage.py test pharmacy.tests
```

### 6. Create Admin User
```bash
python manage.py createsuperuser --mobile 080XXXXXXXX --username admin
```

### 7. Run Development Server
```bash
python manage.py runserver
```

## Usage Guide

### For Pharmacists
1. **Login**: Use mobile number and password
2. **Dispense**: Search drugs → Add to cart → Generate receipt
3. **Inventory Check**: View low stock alerts and expiring items
4. **Returns**: Use return feature for stock adjustments

### For Admins
1. **User Management**: Register new users via admin panel
2. **Inventory Management**: Add/edit drugs across all categories
3. **Reporting**: Access sales and inventory reports
4. **Form Management**: View and edit past receipts

## API Structure (Future Enhancements)

The service layer is designed to easily support REST API:
```python
# Example service usage
from pharmacy.services import DrugService

# Search drugs
results = DrugService.search_drugs(query='aspirin', category='all')

# Update stock
drug = DrugService.update_stock('lpacemaker', 123, 10, 'subtract')
```

## Environment Configuration

### Required Variables
- `DJANGO_SECRET_KEY`: Cryptographic secret key
- `DEBUG`: True for development, False for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

### Optional Security Variables
- `SECURE_SSL_REDIRECT`: Enable HTTPS redirect
- `SESSION_COOKIE_SECURE`: Secure session cookies
- `CSRF_COOKIE_SECURE`: Secure CSRF cookies

## Running Tests
```bash
# Run all tests
python manage.py test pharmacy.tests

# Run specific test class
python manage.py test pharmacy.tests.DrugServiceTests

# Run with verbose output
python manage.py test pharmacy.tests --verbosity=2
```

## Production Deployment Checklist

### Security
- [ ] Set `DEBUG=False`
- [ ] Generate strong `DJANGO_SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to production domains
- [ ] Enable all security settings in `.env`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure proper web server (not dev server)
- [ ] Set up SSL/HTTPS

### Performance
- [ ] Run database migrations
- [ ] Set up caching (Redis/Memcached)
- [ ] Configure static files serving
- [ ] Set up monitoring and logging
- [ ] Add database backup strategy

### Monitoring
- [ ] Check logs directory exists
- [ ] Configure email for error notifications
- [ ] Set up log rotation
- [ ] Monitor database performance

## Troubleshooting

### Common Issues

1. **Environment variables not loading**
   - Ensure `.env` file exists in project root
   - Check python-dotenv is installed

2. **CSRF verification failed**
   - Ensure CSRF tokens are included in AJAX requests
   - Check that `@csrf_protect` decorator is applied

3. **Database locked errors**
   - The service layer uses transactions properly
   - Check for long-running queries

4. **Stock calculation errors**
   - All calculations use Decimal for precision
   - Validation prevents negative values

## Support
For issues or questions, check the logs directory for detailed error messages.

---
**Version**: 2.0 (Improved)
**Last Updated**: 2026-01-07
