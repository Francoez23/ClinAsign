import math
import time

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from scheduling.models import DutyGroup, DutyGroupMembership

from .models import Profile


class AccountLoginForm(AuthenticationForm):
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 30
    FAILED_ATTEMPTS_SESSION_KEY = 'login_failed_attempts'
    LOCKOUT_UNTIL_SESSION_KEY = 'login_lockout_until'
    INVALID_CREDENTIALS_MESSAGE = 'Invalid Student ID or Password. Please try again.'
    LOCKOUT_MESSAGE = 'Too many failed attempts. Please try again later.'

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.lockout_active = False
        self.lockout_seconds_remaining = 0
        self.lockout_active = self._has_active_lockout()

    def _get_session(self):
        return getattr(self.request, 'session', None)

    def _clear_attempt_state(self):
        session = self._get_session()
        if not session:
            return
        session.pop(self.FAILED_ATTEMPTS_SESSION_KEY, None)
        session.pop(self.LOCKOUT_UNTIL_SESSION_KEY, None)
        session.modified = True

    def _get_lockout_seconds_remaining(self):
        session = self._get_session()
        if not session:
            return 0

        lockout_until = float(session.get(self.LOCKOUT_UNTIL_SESSION_KEY, 0) or 0)
        remaining = max(0, math.ceil(lockout_until - time.time()))
        return remaining

    def _has_active_lockout(self):
        session = self._get_session()
        if not session or self.LOCKOUT_UNTIL_SESSION_KEY not in session:
            self.lockout_seconds_remaining = 0
            return False

        remaining = self._get_lockout_seconds_remaining()
        if remaining > 0:
            self.lockout_seconds_remaining = remaining
            return True

        self._clear_attempt_state()
        self.lockout_seconds_remaining = 0
        return False

    def _register_failed_attempt(self):
        session = self._get_session()
        if not session:
            return False

        attempts = int(session.get(self.FAILED_ATTEMPTS_SESSION_KEY, 0)) + 1
        if attempts >= self.MAX_FAILED_ATTEMPTS:
            session[self.LOCKOUT_UNTIL_SESSION_KEY] = time.time() + self.LOCKOUT_SECONDS
            session.pop(self.FAILED_ATTEMPTS_SESSION_KEY, None)
            session.modified = True
            self.lockout_active = True
            self.lockout_seconds_remaining = self.LOCKOUT_SECONDS
            return True

        session[self.FAILED_ATTEMPTS_SESSION_KEY] = attempts
        session.modified = True
        self.lockout_active = False
        self.lockout_seconds_remaining = 0
        return False

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if self._has_active_lockout():
            raise forms.ValidationError(self.LOCKOUT_MESSAGE, code='too_many_attempts')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                if self._register_failed_attempt():
                    raise forms.ValidationError(self.LOCKOUT_MESSAGE, code='too_many_attempts')
                raise forms.ValidationError(
                    self.INVALID_CREDENTIALS_MESSAGE,
                    code='invalid_login',
                )

            self.confirm_login_allowed(self.user_cache)
            self._clear_attempt_state()

        return self.cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)

    class Meta:
        model = Profile
        fields = ['year_level', 'section', 'phone_number']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email


class StudentAccountBaseForm(forms.ModelForm):
    school_id = forms.CharField(max_length=30, label='School ID')
    year_level = forms.CharField(required=False)
    section = forms.CharField(required=False)
    phone_number = forms.CharField(required=False)
    duty_groups = forms.ModelMultipleChoiceField(
        queryset=DutyGroup.objects.none(),
        required=False,
        label='Assigned classes',
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        self.instructor = kwargs.pop('instructor')
        self.profile = kwargs.pop('profile', None)
        instance = self.profile.user if self.profile else kwargs.pop('instance', None)
        super().__init__(*args, instance=instance, **kwargs)
        instructor_groups = DutyGroup.objects.filter(instructor=self.instructor).order_by('name')
        self.fields['duty_groups'].queryset = instructor_groups
        self.fields['duty_groups'].help_text = 'Assigned students can be scheduled in these classes.'

        if self.profile:
            self.fields['school_id'].initial = self.profile.student_id
            self.fields['year_level'].initial = self.profile.year_level
            self.fields['section'].initial = self.profile.section
            self.fields['phone_number'].initial = self.profile.phone_number
            self.fields['duty_groups'].initial = instructor_groups.filter(
                memberships__student=self.profile.user
            ).distinct()

    def clean_school_id(self):
        school_id = self.cleaned_data['school_id'].strip().upper()
        if not school_id:
            raise forms.ValidationError('School ID is required.')

        username_conflict = User.objects.filter(username__iexact=school_id)
        student_id_conflict = Profile.objects.filter(student_id__iexact=school_id)

        if self.instance.pk:
            username_conflict = username_conflict.exclude(pk=self.instance.pk)
        if self.profile and self.profile.pk:
            student_id_conflict = student_id_conflict.exclude(pk=self.profile.pk)

        if username_conflict.exists() or student_id_conflict.exists():
            raise forms.ValidationError('This School ID is already in use.')
        return school_id

    def _save_student_profile(self, user):
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = Profile.ROLE_STUDENT
        profile.student_id = self.cleaned_data['school_id']
        profile.created_by = self.instructor
        profile.year_level = self.cleaned_data.get('year_level', '')
        profile.section = self.cleaned_data.get('section', '')
        profile.phone_number = self.cleaned_data.get('phone_number', '')
        profile.save()

    def _sync_duty_groups(self, user):
        assigned_groups = self.cleaned_data['duty_groups']
        DutyGroupMembership.objects.filter(
            student=user,
            duty_group__instructor=self.instructor,
        ).exclude(duty_group__in=assigned_groups).delete()
        for duty_group in assigned_groups:
            DutyGroupMembership.objects.get_or_create(duty_group=duty_group, student=user)

    def save(self, commit=True):
        school_id = self.cleaned_data['school_id']
        user = super().save(commit=False)
        user.username = school_id

        if not commit:
            return user

        user.save()
        self._save_student_profile(user)
        self._sync_duty_groups(user)

        return user


class StudentAccountCreateForm(StudentAccountBaseForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Confirm password')

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')

        if password:
            candidate_user = User(
                username=cleaned_data.get('school_id', ''),
                first_name=cleaned_data.get('first_name', ''),
                last_name=cleaned_data.get('last_name', ''),
                email=cleaned_data.get('email', ''),
            )
            validate_password(password, user=candidate_user)

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            self._save_student_profile(user)
            self._sync_duty_groups(user)
        return user


class StudentAccountUpdateForm(StudentAccountBaseForm):
    pass
