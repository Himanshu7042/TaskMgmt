from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class TaskManager(models.Manager):
    def overdue(self):
        today = timezone.localdate()
        # Returns tasks where due_date is in the past AND status is not DONE
        return self.filter(due_date__lt=today).exclude(status='DONE')


class Task(models.Model):
    STATUS_CHOICES = [
        ('TO DO', 'To Do'),
        ('IN PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]

    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TO DO')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='LOW')
    due_date = models.DateField()

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    created_at = models.DateTimeField(auto_now_add=True)

    # Hook up the custom manager
    objects = TaskManager()

    class Meta:
        indexes = [
            models.Index(fields=['status', 'due_date'], name='idx_status_due_date'),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.title}"



