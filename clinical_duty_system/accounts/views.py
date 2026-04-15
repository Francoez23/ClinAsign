from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, redirect_to_login
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from scheduling.models import DutyGroupMembership

from .forms import (
    AccountLoginForm,
    ProfileUpdateForm,
    StudentAccountCreateForm,
    StudentAccountUpdateForm,
)
from .models import Profile


def instructor_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.profile.role != Profile.ROLE_INSTRUCTOR:
            return HttpResponseForbidden('You are not authorized to access this page.')
        return view_func(request, *args, **kwargs)

    return never_cache(wrapped)


def register(request):
    messages.info(
        request,
        'Student self-registration is disabled. Please ask your instructor to create your account.',
    )
    return redirect('login')


@method_decorator(never_cache, name='dispatch')
class AccountLoginView(LoginView):
    authentication_form = AccountLoginForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


@method_decorator(never_cache, name='dispatch')
class AccountLogoutView(LogoutView):
    next_page = reverse_lazy('login')


def _save_profile_updates(request, form):
    request.user.first_name = form.cleaned_data['first_name']
    request.user.last_name = form.cleaned_data['last_name']
    request.user.email = form.cleaned_data['email']
    request.user.save()
    form.save()


@never_cache
@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile, user=request.user)
        if form.is_valid():
            _save_profile_updates(request, form)
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile, user=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@instructor_required
def student_list(request):
    managed_memberships = DutyGroupMembership.objects.filter(
        duty_group__instructor=request.user
    ).select_related('duty_group')
    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT,
        created_by=request.user,
    ).select_related('user').prefetch_related(
        Prefetch('user__duty_group_memberships', queryset=managed_memberships, to_attr='managed_memberships')
    ).order_by('student_id', 'user__last_name', 'user__first_name')
    return render(request, 'accounts/student_list.html', {'students': students})


@instructor_required
def student_create(request):
    if request.method == 'POST':
        form = StudentAccountCreateForm(request.POST, instructor=request.user)
        if form.is_valid():
            with transaction.atomic():
                student = form.save()
            messages.success(
                request,
                f'Student account for {student.get_full_name() or student.username} was created successfully.',
            )
            return redirect('student-list')
    else:
        form = StudentAccountCreateForm(instructor=request.user)

    return render(
        request,
        'accounts/student_form.html',
        {'form': form, 'title': 'Create Student Account', 'submit_label': 'Create Account'},
    )


@instructor_required
def student_update(request, pk):
    student_profile = get_object_or_404(
        Profile.objects.select_related('user'),
        pk=pk,
        role=Profile.ROLE_STUDENT,
        created_by=request.user,
    )

    if request.method == 'POST':
        form = StudentAccountUpdateForm(
            request.POST,
            instructor=request.user,
            profile=student_profile,
        )
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, 'Student account updated successfully.')
            return redirect('student-list')
    else:
        form = StudentAccountUpdateForm(instructor=request.user, profile=student_profile)

    return render(
        request,
        'accounts/student_form.html',
        {'form': form, 'title': 'Manage Student Account', 'submit_label': 'Save Changes'},
    )


@method_decorator(never_cache, name='dispatch')
class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    login_url = reverse_lazy('login')
    template_name = 'registration/password_change_form.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, 'Password updated successfully.')
        return super().form_valid(form)
