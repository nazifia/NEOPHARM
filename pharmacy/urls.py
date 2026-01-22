from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.index, name='index'),
    path('store/', views.store, name='store'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dispense/', views.dispense, name='dispense'),
    path('cart/', views.cart, name='cart'),
    path('receipt/', views.receipt, name='receipt'),
    path('receipt/<str:receipt_id>/', views.receipt_detail, name='receipt_detail'),
    path('logout/', views.logout_user, name='logout_user'),
    path('add-item/', views.add_item, name='add_item'),
    path('edit-item/<str:drug_type>/<int:pk>/', views.edit_item, name='edit_item'),
    path('delete-item/<str:drug_type>/<int:pk>/', views.delete_item, name='delete_item'),

    # Cart management
    path('cart/clear/', views.clear_cart, name='clear_cart'),

    # Consolidated return item URL
    path('return/<str:drug_type>/<int:pk>/', views.return_item, name='return_item'),

    # HTMX endpoints

    path('quick-dispense/<str:drug_type>/<int:pk>/', views.quick_dispense, name='quick_dispense'),
    path('add-to-cart/<str:drug_type>/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<str:pk>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<str:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('search/', views.search_item, name='search_items'),
    path('register/', views.register_user, name='register'),
    path('profile/', views.profile, name='profile'),
    path('forms/', views.form_list, name='forms'),
    path('forms/<str:form_id>/', views.view_form, name='view_form'),
    path('forms/<str:form_id>/edit/', views.edit_form, name='edit_form'),
    path('forms/<str:form_id>/items/add/', views.add_form_item, name='add_form_item'),
    path('forms/<str:form_id>/items/<int:item_id>/edit/', views.edit_form_item, name='edit_form_item'),
    path('forms/<str:form_id>/items/<int:item_id>/remove/', views.remove_form_item, name='remove_form_item'),
    path('search-items/', views.search_items, name='search_items'),
    path('get-category-drugs/', views.get_category_drugs, name='get_category_drugs'),

    # Admin User & Permission Management URLs
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', views.admin_users_list, name='admin_users_list'),
    path('admin/users/create/', views.admin_user_create, name='admin_user_create'),
    path('admin/users/<int:user_id>/edit/', views.admin_user_edit, name='admin_user_edit'),
    path('admin/users/<int:user_id>/delete/', views.admin_user_delete, name='admin_user_delete'),
    path('admin/users/<int:user_id>/permissions/', views.admin_user_permissions, name='admin_user_permissions'),
    path('admin/groups/', views.admin_groups_list, name='admin_groups_list'),
    path('admin/groups/create/', views.admin_group_create, name='admin_group_create'),
    path('admin/groups/<int:group_id>/edit/', views.admin_group_edit, name='admin_group_edit'),
    path('admin/groups/<int:group_id>/delete/', views.admin_group_delete, name='admin_group_delete'),
    path('admin/groups/<int:group_id>/', views.admin_group_view, name='admin_group_view'),
    # Quick category views
    path('admin/users/category/<str:category>/', views.admin_users_list, name='admin_users_by_category'),
    
    # Password management
    path('admin/users/<int:user_id>/change-password/', views.admin_user_change_password, name='admin_user_change_password'),
    path('admin/users/<int:user_id>/set-password/', views.admin_profile_password_change, name='admin_set_password'),
    path('profile/change-password/', views.profile_change_password, name='profile_change_password'),
    
    # Model Name Editing URLs
    path('admin/model-browser/', views.model_browser, name='model_browser'),
    path('admin/model-browser/select/', views.select_model_category, name='select_model_category'),
    path('admin/model-browser/<str:category>/', views.admin_model_list, name='admin_model_list'),
    path('admin/model-browser/<str:category>/<int:drug_id>/edit/', views.admin_edit_model_name, name='admin_edit_model_name'),
    
    # API endpoints
    path('api/extend-session/', views.extend_session, name='extend_session'),
]
