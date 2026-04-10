from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from scheduling.models import DutyGroup, DutyGroupMembership

from .models import Profile


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
