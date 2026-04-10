from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from accounts.models import Profile
from .forms import ClinicalAreaForm, DutyGroupForm, DutyScheduleForm, JoinDutyGroupForm, PatientCaseForm
from .models import (
    ClinicalArea,
    DutyGroup,
    DutyGroupMembership,
    DutyHistory,
    DutySchedule,
    Notification,
    PatientCase,
)

def role_required(*allowed_roles):
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.profile.role not in allowed_roles:
                return HttpResponseForbidden('You are not authorized to access this page.')
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


@login_required
def dashboard(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    context = {'profile': profile}

    if profile.role == Profile.ROLE_ADMIN:
        context.update({
            'total_users': User.objects.count(),
            'total_students': User.objects.filter(profile__role=Profile.ROLE_STUDENT).count(),
            'total_instructors': User.objects.filter(profile__role=Profile.ROLE_INSTRUCTOR).count(),
            'clinical_areas': ClinicalArea.objects.count(),
            'recent_notifications': Notification.objects.all()[:5],
        })
    elif profile.role == Profile.ROLE_INSTRUCTOR:
        instructor_schedules = DutySchedule.objects.filter(instructor=request.user)
        instructor_groups = DutyGroup.objects.filter(instructor=request.user).annotate(
            student_count=Count('students', distinct=True)
        )
        context.update({
            'class_count': instructor_groups.count(),
            'managed_student_count': Profile.objects.filter(
                role=Profile.ROLE_STUDENT,
                created_by=request.user,
            ).count(),
            'joined_student_count': User.objects.filter(
                duty_group_memberships__duty_group__instructor=request.user
            ).distinct().count(),
            'schedule_count': instructor_schedules.count(),
            'case_count': PatientCase.objects.filter(duty_schedule__instructor=request.user).count(),
            'duty_groups': instructor_groups[:5],
            'recent_schedules': instructor_schedules[:5],
            'exposure_summary': DutyHistory.objects.filter(
                duty_schedule__instructor=request.user
            ).values('exposure_type').annotate(total=Count('id')).order_by('-total')[:5],
        })
    else:
        student_schedules = DutySchedule.objects.filter(student=request.user)
        joined_groups = DutyGroupMembership.objects.filter(student=request.user).select_related(
            'duty_group',
            'duty_group__instructor',
        )
        context.update({
            'class_count': joined_groups.count(),
            'schedule_count': student_schedules.count(),
            'assigned_cases': PatientCase.objects.filter(duty_schedule__student=request.user).count(),
            'joined_groups': joined_groups[:5],
            'recent_schedules': student_schedules[:5],
            'notifications': Notification.objects.filter(user=request.user)[:5],
        })

    return render(request, 'scheduling/dashboard.html', context)


@role_required(Profile.ROLE_ADMIN)
def clinical_area_list(request):
    areas = ClinicalArea.objects.all()
    return render(request, 'scheduling/clinical_area_list.html', {'areas': areas})


@role_required(Profile.ROLE_ADMIN)
def clinical_area_create(request):
    if request.method == 'POST':
        form = ClinicalAreaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinical area created successfully.')
            return redirect('clinical-area-list')
    else:
        form = ClinicalAreaForm()
    return render(request, 'scheduling/form.html', {'form': form, 'title': 'Add Clinical Area'})


@role_required(Profile.ROLE_INSTRUCTOR)
def schedule_list(request):
    if request.user.profile.role == Profile.ROLE_INSTRUCTOR:
        schedules = DutySchedule.objects.filter(instructor=request.user)
    else:
        schedules = DutySchedule.objects.filter(student=request.user)
    return render(request, 'scheduling/schedule_list.html', {'schedules': schedules})


@role_required(Profile.ROLE_INSTRUCTOR)
def schedule_create(request):
    if request.method == 'POST':
        form = DutyScheduleForm(request.POST, instructor=request.user)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.instructor = request.user
            schedule.save()
            Notification.objects.create(
                user=schedule.student,
                title='New Duty Schedule',
                message=f'You have been assigned to {schedule.clinical_area.name} on {schedule.duty_date}.',
            )
            messages.success(request, 'Duty schedule created successfully.')
            return redirect('schedule-list')
    else:
        form = DutyScheduleForm(instructor=request.user)

    if not form.fields['student'].queryset.exists():
        messages.info(
            request,
            'No students are assigned to your classes yet. Create a class and assign or invite students first.',
        )

    return render(request, 'scheduling/form.html', {'form': form, 'title': 'Create Duty Schedule'})


@role_required(Profile.ROLE_INSTRUCTOR)
def schedule_update(request, pk):
    schedule = get_object_or_404(DutySchedule, pk=pk, instructor=request.user)
    if request.method == 'POST':
        form = DutyScheduleForm(request.POST, instance=schedule, instructor=request.user)
        if form.is_valid():
            schedule = form.save()
            Notification.objects.create(
                user=schedule.student,
                title='Duty Schedule Updated',
                message=f'Your duty schedule for {schedule.duty_date} has been updated.',
            )
            messages.success(request, 'Duty schedule updated successfully.')
            return redirect('schedule-list')
    else:
        form = DutyScheduleForm(instance=schedule, instructor=request.user)
    return render(request, 'scheduling/form.html', {'form': form, 'title': 'Update Duty Schedule'})


@role_required(Profile.ROLE_INSTRUCTOR, Profile.ROLE_STUDENT)
def student_schedule_list(request):
    schedules = DutySchedule.objects.filter(student=request.user)
    return render(request, 'scheduling/schedule_list.html', {'schedules': schedules})


@role_required(Profile.ROLE_INSTRUCTOR, Profile.ROLE_STUDENT)
def group_list(request):
    profile = request.user.profile

    if profile.role == Profile.ROLE_INSTRUCTOR:
        groups = DutyGroup.objects.filter(instructor=request.user).annotate(
            student_count=Count('students', distinct=True)
        ).prefetch_related('memberships__student')
        return render(request, 'scheduling/group_list.html', {'groups': groups, 'profile': profile})

    memberships = DutyGroupMembership.objects.filter(student=request.user).select_related(
        'duty_group',
        'duty_group__instructor',
    )
    return render(request, 'scheduling/group_list.html', {'memberships': memberships, 'profile': profile})


@role_required(Profile.ROLE_INSTRUCTOR)
def group_create(request):
    if request.method == 'POST':
        form = DutyGroupForm(request.POST, instructor=request.user)
        if form.is_valid():
            duty_group = form.save(commit=False)
            duty_group.instructor = request.user
            duty_group.save()
            messages.success(
                request,
                f'Class created successfully. Share code {duty_group.join_code} with your students.',
            )
            return redirect('group-list')
    else:
        form = DutyGroupForm(instructor=request.user)

    return render(
        request,
        'scheduling/form.html',
        {
            'form': form,
            'title': 'Create Class',
            'description': 'Create an instructor class and share the generated class code with your students.',
            'submit_label': 'Create Class',
        },
    )


@role_required(Profile.ROLE_STUDENT)
def group_join(request):
    if request.method == 'POST':
        form = JoinDutyGroupForm(request.POST, student=request.user)
        if form.is_valid():
            membership = form.save()
            Notification.objects.create(
                user=request.user,
                title='Class Joined',
                message=f'You joined {membership.duty_group.name} successfully.',
            )
            Notification.objects.create(
                user=membership.duty_group.instructor,
                title='New Student Joined',
                message=(
                    f'{request.user.get_full_name() or request.user.username} joined '
                    f'{membership.duty_group.name}.'
                ),
            )
            messages.success(request, f'You joined {membership.duty_group.name}.')
            return redirect('group-list')
    else:
        form = JoinDutyGroupForm(student=request.user)

    return render(
        request,
        'scheduling/form.html',
        {
            'form': form,
            'title': 'Join Class',
            'description': 'Enter the class code shared by your instructor to join their class.',
            'submit_label': 'Join Class',
        },
    )


@role_required(Profile.ROLE_INSTRUCTOR)
def patient_case_list(request):
    cases = PatientCase.objects.filter(duty_schedule__instructor=request.user)
    return render(request, 'scheduling/patient_case_list.html', {'cases': cases})


@role_required(Profile.ROLE_INSTRUCTOR)
def patient_case_create(request):
    if request.method == 'POST':
        form = PatientCaseForm(request.POST, instructor=request.user)
        if form.is_valid():
            patient_case = form.save()
            DutyHistory.objects.create(
                student=patient_case.duty_schedule.student,
                duty_schedule=patient_case.duty_schedule,
                patient_case=patient_case,
                exposure_type=patient_case.diagnosis,
                completed_on=patient_case.duty_schedule.duty_date,
            )
            Notification.objects.create(
                user=patient_case.duty_schedule.student,
                title='New Patient Case Assignment',
                message=f'You have been assigned case: {patient_case.case_title}.',
            )
            messages.success(request, 'Patient case assigned successfully.')
            return redirect('patient-case-list')
    else:
        form = PatientCaseForm(instructor=request.user)
    return render(request, 'scheduling/form.html', {'form': form, 'title': 'Assign Patient Case'})


@role_required(Profile.ROLE_STUDENT)
def my_cases(request):
    cases = PatientCase.objects.filter(duty_schedule__student=request.user)
    return render(request, 'scheduling/patient_case_list.html', {'cases': cases})


@login_required
def notifications(request):
    items = Notification.objects.filter(user=request.user)
    return render(request, 'scheduling/notifications.html', {'notifications': items})
