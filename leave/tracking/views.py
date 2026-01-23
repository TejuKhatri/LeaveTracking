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
    return render(request, 'admin_dashboard.html', context)

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
    
    return render(request, 'leave_history.html', {'leave_requests': leave_requests})

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
        try:
            user = CustomUser.objects.get(email=email)
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # In production, send email here
            # For now, just show success message
            messages.success(request, 'Password reset link has been sent to your email!')
            return redirect('login')
        except CustomUser.DoesNotExist:
            messages.error(request, 'No user found with this email address')
    
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