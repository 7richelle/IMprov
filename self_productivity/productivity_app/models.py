from django.db import models

# Create your models here.

from django.contrib.auth.models import User

from django.utils import timezone
import datetime

class Task(models.Model):
    TASK_TYPE_CHOICES = [
        ('stationary', 'Stationary'),
        ('active', 'Active'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    FREQUENCY_CHOICES = [
        ('today', 'Today'),
        ('daily_week', 'Daily for a Week'),
    ]
    DURATION_CHOICES = [
        ('5min', '5 mins'),
        ('10min', '10 mins'),
        ('30min', '30 mins'),
        ('1hr', '1 hour'),
    ]
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')

    def __str__(self):
        return f"{self.description[:30]}..."


##class TaskSession(models.Model):
  ##  task = models.ForeignKey(Task, on_delete=models.CASCADE)
     ##  start_time = models.DateTimeField(auto_now_add=True)
     ##  end_time = models.DateTimeField(null=True, blank=True)
     ##  completion_status = models.CharField(max_length=20, default='in_progress')


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=timezone.now)

    def is_valid(self):
        # OTP valid for 5 minutes
        return timezone.now() - self.created_at < datetime.timedelta(minutes=5)
