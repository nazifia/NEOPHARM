# Admin Interface Guide - User & Permission Management

The pharmacy system now includes a comprehensive admin interface for managing user permissions and groups.

## Accessing the Admin Interface

### Via Dashboard
1. Log in as a staff user or superuser
2. Navigate to the Dashboard
3. Click on **"Admin Panel"** in the Quick Actions

### Direct URL
- Admin Dashboard: `/admin/`
- Users Management: `/admin/users/`
- Groups Management: `/admin/groups/`

## Features

### User Management
- **View All Users**: See all registered users with details (username, mobile, role, status)
- **Create Users**: New superuser-friendly interface to create and configure users
  - Set username, mobile, full name, and role
  - Configure staff and superuser status
  - Set passwords
- **Edit Users**: Modify user details and permissions
- **Delete Users**: Remove user accounts (superusers only, can't delete self)
- **Manage Permissions**: Assign groups and individual permissions to users

### Group Management
- **View All Groups**: See all groups with member and permission counts
- **Create Groups**: Create new permission groups
- **Edit Groups**: Modify group name and permissions
- **Delete Groups**: Remove permission groups
- **View Details**: See complete group membership and assigned permissions

### Admin Dashboard
- **User Statistics**: Total users, active users, staff, superusers, total groups
- **Recent Activity**: Quick view of recently created users
- **Quick Navigation**: Fast access to user and group management

## URL Routes

```python
# Admin Dashboard
store:admin_dashboard           # /admin/

# User Management
store:admin_users_list          # /admin/users/
store:admin_user_create         # /admin/users/create/
store:admin_user_edit           # /admin/users/<id>/edit/
store:admin_user_delete         # /admin/users/<id>/delete/
store:admin_user_permissions    # /admin/users/<id>/permissions/

# Group Management
store:admin_groups_list         # /admin/groups/
store:admin_group_create        # /admin/groups/create/
store:admin_group_edit          # /admin/groups/<id>/edit/
store:admin_group_delete        # /admin/groups/<id>/delete/
store:admin_group_view          # /admin/groups/<id>/
```

## Security Features

### Access Control
- Only **staff users** and **superusers** can access admin pages
- **Superusers only** can create/delete users and manage permissions
- Users cannot delete their own accounts
- Superusers cannot be deleted by anyone

### Permission Granularity
- **Groups** provide role-based access control
- **Individual permissions** can be assigned directly to users
- Permissions include:
  - User management (add, change, delete, view)
  - Group management (add, change, delete, view)
  - Pharmacy models (Lpacemaker, NCAP, Oncology drugs) view/change/delete

## User Interface

### Clean Layout
- Responsive design with Bootstrap 5
- Tooltips for helpful hints
- Loading states and feedback messages
- Form validation with clear error messages

### Confirmation Dialogs
- Delete operations require confirmation (type the name to confirm)
- Warning messages for destructive actions
- Visual alerts for security-sensitive operations

## Example Workflows

### Creating a New Staff Member
1. Go to Admin Dashboard
2. Click "Create User" or go to `/admin/users/create/`
3. Fill in:
   - Username: `newpharm`
   - Mobile: `08031234567`
   - Full Name: `John Doe`
   - Role: `Pharmacist`
   - Password: `securepass123`
   - Active: ✓
   - Staff: ✓
4. Click "Create User"

### Assigning Permissions to a User
1. Go to User Management
2. Find the user and click the Lock icon (Permissions)
3. In the user's profile, scroll to permission management
4. Select Groups (e.g., "Pharmacists")
5. Select individual permissions if needed
6. Click "Update Permissions"

### Creating a Role-Based Group
1. Go to Group Management
2. Click "Create Group"
3. Enter name: `Pharmacy Assistants`
4. Select permissions such as:
   - `pharmacy.view_lpacemaker`
   - `pharmacy.view_ncap`
   - `pharmacy.view_oncology`
   - `auth.view_user`
5. Click "Create Group"

## URL Integration with Existing System

The new admin routes integrate with your existing pharmacy URL structure:
- All routes are prefixed with `/store/` (e.g., `/store/admin/`)
- Accessible via the existing authentication system
- Uses the same base template and styling
- Maintains session timeout behavior
- Compatible with existing user model

## Testing

To quickly test the admin interface:

```bash
# Log in as superuser
# Mobile: 08032194090
# Password: (use your superuser password)

# Navigate to:
1. Dashboard → Click "Admin Panel"
2. Or directly: http://localhost:8000/store/admin/

# Test user creation:
- Create user: `staff_user`, mobile: `09036789012`
- Set as Staff, normal User

# Test group creation:
- Create group: `Test Group`
- Assign some permissions
- Add users to the group
```

## Notes

- All admin views include proper error handling and security checks
- Templates use inline CSS for maximum compatibility
- Forms include client-side validation where appropriate
- The interface is mobile-responsive
- All actions are logged with success/error messages
- Permissions are inherited from Django's built-in auth system

## Troubleshooting

### "Permission Denied" Error
- Ensure you're logged in with a staff or superuser account
- Check if your user has `is_staff=True` or `is_superuser=True`

### "Only superusers can..." Error
- Create permissions requires superuser status
- Regular staff users can only view and manage profiles with proper permissions assigned

### Template Loading Issues
- Templates are placed in `pharmacy/templates/store/admin/`
- Check that `DIRS` in settings.py includes the templates directory

### Permission Not Taking Effect
- Permissions need to be assigned to groups or users
- Users need to log out and log in again for permission changes to take effect
- Superusers have all permissions automatically
