# khora/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import CustomUser, LeaveRequest
from .forms import SignUpForm, LeaveRequestForm, LeaveApprovalForm

def home(request):
    """Home page view"""
    return render(request, 'home.html')

def signup_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('user_dashboard' if request.user.role == 'user' else 'admin_dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('user_dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('user_dashboard' if request.user.role == 'user' else 'admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            if user.role == 'admin':
                return redirect('admin_dashboard')
            return redirect('user_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

@login_required
def profile_view(request):
    """User profile view"""
    if request.method == 'POST':
        user = request.user
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.department = request.POST.get('department', user.department)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'profile.html')

@login_required
def create_admin(request):
    """Create new admin user (only accessible by existing admins)"""
    if request.user.role != 'admin':
        messages.error(request, 'Only admins can create new admin accounts')
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        department = request.POST.get('department')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Check if username already exists
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'create_admin.html')
        
        # Create new admin user
        admin_user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='admin',
            phone=phone,
            department=department,
            first_name=first_name,
            last_name=last_name
        )
        
        messages.success(request, f'Admin user "{username}" created successfully!')
        return redirect('admin_dashboard')
    
    return render(request, 'create_admin.html')

@login_required
def user_dashboard(request):
    """User dashboard showing their leave requests"""
    if request.user.role == 'admin':
        return redirect('admin_dashboard')
    
    leave_requests = LeaveRequest.objects.filter(user=request.user)
    pending_count = leave_requests.filter(status='pending').count()
    approved_count = leave_requests.filter(status='approved').count()
    rejected_count = leave_requests.filter(status='rejected').count()
    
    context = {
        'leave_requests': leave_requests[:5],
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'user_dashboard.html', context)

@login_required
def admin_dashboard(request):
    """Admin dashboard showing all leave requests"""
    if request.user.role != 'admin':
        return redirect('user_dashboard')
    
    # Redirect to the new admin home page for better UX
    return redirect('admin_home')

@login_required
def admin_requests(request):
    """Admin requests dashboard (old dashboard functionality)"""
    if request.user.role != 'admin':
        return redirect('user_dashboard')
    
    leave_requests = LeaveRequest.objects.all()
    pending_requests = leave_requests.filter(status='pending')
    approved_requests = leave_requests.filter(status='approved')
    rejected_requests = leave_requests.filter(status='rejected')
    
    context = {
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'total_users': CustomUser.objects.filter(role='user').count(),
    }
    return render(request, 'admin/dashboard.html', context)

@login_required
def submit_leave(request):
    """Submit new leave request"""
    if request.user.role == 'admin':
        messages.warning(request, 'Admins cannot submit leave requests')
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.user = request.user
            leave_request.save()
            messages.success(request, 'Leave request submitted successfully!')
            return redirect('user_dashboard')
    else:
        form = LeaveRequestForm()
    
    return render(request, 'submit_leave.html', {'form': form})

@login_required
def edit_leave(request, leave_id):
    """Edit leave request (only if pending)"""
    leave_request = get_object_or_404(LeaveRequest, id=leave_id, user=request.user)
    
    if leave_request.status != 'pending':
        messages.error(request, 'You can only edit pending leave requests')
        return redirect('user_dashboard')
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, instance=leave_request)
        if form.is_valid():
            form.save()
            messages.success(request, 'Leave request updated successfully!')
            return redirect('user_dashboard')
    else:
        form = LeaveRequestForm(instance=leave_request)
    
    return render(request, 'edit_leave.html', {'form': form, 'leave_request': leave_request})

@login_required
def delete_leave(request, leave_id):
    """Delete leave request"""
    if request.user.role == 'admin':
        leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    else:
        leave_request = get_object_or_404(LeaveRequest, id=leave_id, user=request.user)
        if leave_request.status != 'pending':
            messages.error(request, 'You can only delete pending leave requests')
            return redirect('user_dashboard')
    
    leave_request.delete()
    messages.success(request, 'Leave request deleted successfully!')
    
    if request.user.role == 'admin':
        return redirect('admin_dashboard')
    return redirect('user_dashboard')

@login_required
def leave_history(request):
    """View leave history"""
    if request.user.role == 'admin':
        leave_requests = LeaveRequest.objects.all()
    else:
        leave_requests = LeaveRequest.objects.filter(user=request.user)
    
    # Calculate statistics
    pending_count = leave_requests.filter(status='pending').count()
    approved_count = leave_requests.filter(status='approved').count()
    rejected_count = leave_requests.filter(status='rejected').count()
    total_count = leave_requests.count()
    
    context = {
        'leave_requests': leave_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
    }
    
    return render(request, 'leave_history.html', context)

@login_required
def update_leave_status(request, leave_id):
    """Admin updates leave status"""
    if request.user.role != 'admin':
        messages.error(request, 'Only admins can update leave status')
        return redirect('user_dashboard')
    
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST, instance=leave_request)
        if form.is_valid():
            form.save()
            messages.success(request, f'Leave request {leave_request.status}!')
            return redirect('admin_dashboard')
    else:
        form = LeaveApprovalForm(instance=leave_request)
    
    return render(request, 'admin_dashboard.html', {'form': form, 'leave_request': leave_request})

def forgot_password(request):
    """Forgot password view"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Always show success message for security reasons
        # This prevents email enumeration attacks
        messages.success(request, 'If an account with this email exists, a password reset link has been sent to your email!')
        
        try:
            user = CustomUser.objects.get(email=email)
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # TODO: In production, send actual email here
            # For development, we just log the reset link
            reset_link = f"http://127.0.0.1:8000/reset-password/{uid}/{token}/"
            print(f"DEBUG: Password reset link for {email}: {reset_link}")
            
            # In a real application, you would send an email like this:
            # send_mail(
            #     'Password Reset Request',
            #     f'Click this link to reset your password: {reset_link}',
            #     'noreply@yoursite.com',
            #     [email],
            #     fail_silently=False,
            # )
            
        except CustomUser.DoesNotExist:
            # Don't reveal that the user doesn't exist
            # Just log it for admin purposes
            print(f"DEBUG: Password reset attempted for non-existent email: {email}")
            pass
        
        return redirect('login')
    
    return render(request, 'forgot_password.html')

def reset_password(request, uidb64, token):
    """Reset password view"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            
            if password == password_confirm:
                user.set_password(password)
                user.save()
                messages.success(request, 'Password reset successfully! Please login.')
                return redirect('login')
            else:
                messages.error(request, 'Passwords do not match')
        
        return render(request, 'reset_password.html', {'valid': True})
    else:
        messages.error(request, 'Invalid reset link')
        return redirect('login')

@login_required
def admin_home(request):
    """Admin home page"""
    # Debug: Print user info
    print(f"DEBUG: User: {request.user}")
    print(f"DEBUG: User role: {getattr(request.user, 'role', 'NO ROLE ATTRIBUTE')}")
    print(f"DEBUG: User is authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: User is admin: {getattr(request.user, 'role', None) == 'admin'}")
    
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.user.role != 'admin':
        print(f"DEBUG: Redirecting to user dashboard because role is '{request.user.role}', not 'admin'")
        return redirect('user_dashboard')
    
    # Get statistics
    total_users = CustomUser.objects.filter(role='user').count()
    total_requests = LeaveRequest.objects.count()
    pending_count = LeaveRequest.objects.filter(status='pending').count()
    approved_count = LeaveRequest.objects.filter(status='approved').count()
    
    # Get recent requests (last 5)
    recent_requests = LeaveRequest.objects.all().order_by('-submitted_on')[:5]
    
    context = {
        'total_users': total_users,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'recent_requests': recent_requests,
    }
    
    print(f"DEBUG: Rendering admin home with context: {context}")
    return render(request, 'admin/home.html', context)

@login_required
def admin_tracking(request):
    """Admin tracking page"""
    print(f"DEBUG TRACKING: User: {request.user}, Role: {getattr(request.user, 'role', 'NO ROLE')}")
    
    if request.user.role != 'admin':
        print(f"DEBUG TRACKING: Redirecting because role is '{request.user.role}'")
        return redirect('user_dashboard')
    
    # Get all leave requests
    leave_requests = LeaveRequest.objects.all().order_by('-submitted_on')
    
    # Apply filters
    search = request.GET.get('search')
    leave_type = request.GET.get('leave_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if search:
        leave_requests = leave_requests.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(reason__icontains=search)
        )
    
    if leave_type:
        leave_requests = leave_requests.filter(leave_type=leave_type)
    
    if date_from:
        leave_requests = leave_requests.filter(start_date__gte=date_from)
    
    if date_to:
        leave_requests = leave_requests.filter(end_date__lte=date_to)
    
    # Calculate statistics
    total_requests = leave_requests.count()
    pending_requests = leave_requests.filter(status='pending').count()
    approved_requests = leave_requests.filter(status='approved').count()
    rejected_requests = leave_requests.filter(status='rejected').count()
    
    # This month requests
    now = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_requests = leave_requests.filter(submitted_on__gte=this_month_start).count()
    
    context = {
        'leave_requests': leave_requests,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'this_month_requests': this_month_requests,
    }
    
    return render(request, 'admin/tracking.html', context)

@login_required
def admin_users(request):
    """Admin users management page"""
    if request.user.role != 'admin':
        return redirect('user_dashboard')
    
    # Get all users
    users = CustomUser.objects.all().order_by('-date_joined')
    
    # Apply search filter
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(department__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Add leave statistics for each user
    users_with_stats = []
    for user in users:
        if user.role == 'user':
            total_requests = LeaveRequest.objects.filter(user=user).count()
            pending_requests = LeaveRequest.objects.filter(user=user, status='pending').count()
            approved_requests = LeaveRequest.objects.filter(user=user, status='approved').count()
            user.total_requests = total_requests
            user.pending_requests = pending_requests
            user.approved_requests = approved_requests
        users_with_stats.append(user)
    
    # Calculate statistics
    total_users = CustomUser.objects.count()
    admin_count = CustomUser.objects.filter(role='admin').count()
    user_count = CustomUser.objects.filter(role='user').count()
    
    # New users this month
    now = timezone.now()
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_count = CustomUser.objects.filter(date_joined__gte=this_month_start).count()
    
    context = {
        'users': users_with_stats,
        'total_users': total_users,
        'admin_count': admin_count,
        'user_count': user_count,
        'new_users_count': new_users_count,
    }
    
    return render(request, 'admin/users.html', context)