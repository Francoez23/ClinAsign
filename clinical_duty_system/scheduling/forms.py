from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from accounts.models import Profile
from .models import ClinicalArea, DutyGroup, DutyGroupMembership, DutySchedule, PatientCase


class ClinicalAreaForm(forms.ModelForm):
    class Meta:
        model = ClinicalArea
        fields = ['name', 'description']


class DutyGroupForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.instructor = kwargs.pop('instructor', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.instructor and DutyGroup.objects.filter(
            instructor=self.instructor,
            name__iexact=name,
        ).exists():
            raise forms.ValidationError('You already have a class with this name.')
        return name

    class Meta:
        model = DutyGroup
        fields = ['name']


class JoinDutyGroupForm(forms.Form):
    join_code = forms.CharField(max_length=10, label='Class code')

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        self.duty_group = None
        super().__init__(*args, **kwargs)
        self.fields['join_code'].widget.attrs['placeholder'] = 'Enter class code'

    def clean_join_code(self):
        join_code = self.cleaned_data['join_code'].strip().upper()
        try:
            self.duty_group = DutyGroup.objects.select_related('instructor').get(join_code=join_code)
        except DutyGroup.DoesNotExist:
            raise forms.ValidationError('Class code not found. Please check the code and try again.')
        return join_code

    def clean(self):
        cleaned_data = super().clean()

        if not self.student:
            raise forms.ValidationError('A student account is required to join a class.')

        if self.student.profile.role != Profile.ROLE_STUDENT:
            raise forms.ValidationError('Only student accounts can join a class using a class code.')

        if self.duty_group and DutyGroupMembership.objects.filter(
            duty_group=self.duty_group,
            student=self.student,
        ).exists():
            raise forms.ValidationError(f'You already joined {self.duty_group.name}.')

        return cleaned_data

    def save(self):
        membership, _ = DutyGroupMembership.objects.get_or_create(
            duty_group=self.duty_group,
            student=self.student,
        )
        return membership


class DutyScheduleForm(forms.ModelForm):
    clinical_area_name = forms.CharField(max_length=100, label='Clinical area')

    class Meta:
        model = DutySchedule
        fields = [
            'title', 'clinical_area_name', 'student', 'duty_date',
            'start_time', 'end_time', 'status', 'notes'
        ]
        widgets = {
            'duty_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        instructor = kwargs.pop('instructor', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.clinical_area_id:
            self.fields['clinical_area_name'].initial = self.instance.clinical_area.name

        student_queryset = User.objects.filter(profile__role=Profile.ROLE_STUDENT)
        if instructor:
            joined_student_ids = DutyGroupMembership.objects.filter(
                duty_group__instructor=instructor
            ).values_list('student_id', flat=True)
            student_filter = Q(pk__in=joined_student_ids)
            if self.instance.pk and self.instance.student_id:
                student_filter |= Q(pk=self.instance.student_id)
            student_queryset = student_queryset.filter(student_filter)

        self.fields['student'].queryset = student_queryset.distinct().order_by('first_name', 'last_name', 'username')
        self.fields['clinical_area_name'].widget.attrs['placeholder'] = 'Enter clinical area'
        self.fields['student'].help_text = 'Students must be assigned to one of your classes before they can be scheduled.'
        if instructor:
            self.instance.instructor = instructor
        self.order_fields(self.Meta.fields)

    def clean_clinical_area_name(self):
        clinical_area_name = self.cleaned_data['clinical_area_name'].strip()
        if not clinical_area_name:
            raise forms.ValidationError('Clinical area is required.')
        return clinical_area_name

    def save(self, commit=True):
        schedule = super().save(commit=False)
        clinical_area_name = self.cleaned_data['clinical_area_name']
        clinical_area = ClinicalArea.objects.filter(name__iexact=clinical_area_name).first()
        if clinical_area is None:
            clinical_area = ClinicalArea.objects.create(name=clinical_area_name)
        schedule.clinical_area = clinical_area

        if commit:
            schedule.save()
            self.save_m2m()
        return schedule


class PatientCaseForm(forms.ModelForm):
    class Meta:
        model = PatientCase
        fields = ['duty_schedule', 'case_title', 'patient_code', 'diagnosis', 'acuity_level', 'remarks']
        widgets = {'remarks': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        instructor = kwargs.pop('instructor', None)
        super().__init__(*args, **kwargs)
        if instructor:
            self.fields['duty_schedule'].queryset = DutySchedule.objects.filter(instructor=instructor)
