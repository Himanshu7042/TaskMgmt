from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from .models import Task, Project, Comment
from .forms import ProjectForm, TaskForm, CommentForm

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Automatically log the user in
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

# Create your views here.

@login_required
def dashboard(request):
    # N+1 Avoidance: select_related fetches the project in the same SQL join
    tasks = Task.objects.filter(assigned_to=request.user).select_related('project')
    
    # Using our custom reusable manager for overdue tasks
    overdue_tasks = Task.objects.overdue().filter(assigned_to=request.user).select_related('project')
    context = {
        'todo_tasks': tasks.filter(status='TO DO'),
        'in_progress_tasks': tasks.filter(status='IN PROGRESS'),
        'done_tasks': tasks.filter(status='DONE'),
        'overdue_tasks': overdue_tasks
    }

    return render(request, 'dashboard.html', context)

@login_required
def project_list(request):
    # Per-project status counts using annotate and Count (NO Python-level counting)
    projects = Project.objects.filter(
        Q(owner=request.user) | Q(tasks__assigned_to=request.user)
    ).distinct().annotate(
        todo_count=Count('tasks', filter=Q(tasks__status='TO DO')),
        in_progress_count=Count('tasks', filter=Q(tasks__status='IN PROGRESS')),
        done_count=Count('tasks', filter=Q(tasks__status='DONE'))
    )
    return render(request, 'project_list.html', {'projects': projects})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)

    is_owner = (project.owner == request.user)
    is_assigned = project.tasks.filter(assigned_to=request.user).exists()

    if not (is_owner or is_assigned):
        return HttpResponseForbidden("You do not have permission to view this project.")

    tasks = project.tasks.all()
    return render(request, 'project_detail.html', {'project': project, 'tasks': tasks, 'is_owner': is_owner, 'is_assigned': is_assigned})


@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'project_form.html', {'form': form})

@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if project.owner != request.user:
        return HttpResponseForbidden("You do not have permission to edit this project.")

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'project_form.html', {'form': form})

def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if project.owner != request.user:
        return HttpResponseForbidden("You do not have permission to delete this project.")

    if request.method == 'POST':
        project.delete()
        return redirect('project_list')

    return render(request, 'project_confirm_delete.html', {'project': project})

@login_required
def task_create(request, project_id):
    project = get_object_or_404(Project, pk=project_id)

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.save()
            return redirect('project_detail', pk=project.pk)
    else:
        form = TaskForm()
    return render(request, 'task_form.html', {'form': form, 'project': project})

@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)

    is_owner = (task.project.owner == request.user)
    is_assigned = (task.assigned_to == request.user)

    if not (is_owner or is_assigned):
        return HttpResponseForbidden("You do not have permission to view this task.")

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            return redirect('task_detail', pk=task.pk)
    else:
        comment_form = CommentForm()

    comments = task.comments.select_related('author').all()

    return render(request, 'task_detail.html', {'task': task, 'comments': comments, 'comment_form': comment_form, 'is_owner': is_owner})

@login_required
def update_task_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        if task.assigned_to == request.user or task.project.owner == request.user:
            new_status = request.POST.get('status')
            if new_status in dict(Task.STATUS_CHOICES):
                task.status = new_status
                task.save()
        else:
            return HttpResponseForbidden("You do not have permission to change this task's status.")
    
    # Redirect back to the referring page if available, else task detail
    next_url = request.META.get('HTTP_REFERER', None)
    if next_url:
        return redirect(next_url)
    return redirect('task_detail', pk=task.pk)

@login_required
def task_update(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if task.project.owner != request.user:
        return HttpResponseForbidden("You do not have permission to edit this task.")

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'task_form.html', {'form': form, 'project': task.project})

@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)

    if task.project.owner != request.user:
        return HttpResponseForbidden("You do not have permission to delete this task.")

    if request.method == 'POST':
        task.delete()
        return redirect('project_detail', pk=task.project.pk)

    return render(request, 'task_confirm_delete.html', {'task': task})
