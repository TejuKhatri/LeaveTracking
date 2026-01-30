# khora/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/home/', views.admin_home, name='admin_home'),
    path('dashboard/admin/requests/', views.admin_requests, name='admin_requests'),
    path('dashboard/admin/tracking/', views.admin_tracking, name='admin_tracking'),
    path('dashboard/admin/users/', views.admin_users, name='admin_users'),
    path('dashboard/admin/create/', views.create_admin, name='create_admin'),
    path('leave/submit/', views.submit_leave, name='submit_leave'),
    path('leave/edit/<int:leave_id>/', views.edit_leave, name='edit_leave'),
    path('leave/delete/<int:leave_id>/', views.delete_leave, name='delete_leave'),
    path('leave/history/', views.leave_history, name='leave_history'),
    path('leave/update/<int:leave_id>/', views.update_leave_status, name='update_leave_status'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
]