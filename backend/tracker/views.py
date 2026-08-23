from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Task

# Create your views here.

@login_required
def dashboard(request):
    tasks = Task.objects.filter(assigned_to=request.user).select_related('project')

    context = {
        'todo_tasks': tasks.filter(status='TODO'),
        'in_progress_tasks': tasks.filter(status='IN_PROGRESS'),
        'done_tasks': tasks.filter(status='DONE'),
    }

    return render(request, 'dashboard.html', context)