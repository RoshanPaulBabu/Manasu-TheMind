from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

class MentalHealthProblem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name
    

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=(('male', 'Male'), ('female', 'Female'), ('other', 'Other')), blank=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    mental_health_problem = models.ForeignKey(MentalHealthProblem, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')


    def __str__(self):
        return self.user.username
    

class Question(models.Model):
    QUESTION_TYPES = [
        ('MC', 'Multiple Choice'),
        ('OE', 'Open Ended'),
    ]

    problem = models.ForeignKey(MentalHealthProblem, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=2, choices=QUESTION_TYPES, default='MC')

    def __str__(self):
        return f"{self.problem.name} - {self.text[:50]}"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.question.text[:50]} - {self.text}"

class UserResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)
    open_ended_response = models.TextField(null=True, blank=True)  # For open-ended questions
    response_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question.text[:50]}"
    
    
class UserResponseHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)
    open_ended_response = models.TextField(null=True, blank=True)
    response_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"History: {self.user.username} - {self.question.text[:50]}  - {self.response_time}"
    
    class Meta:
        ordering = ['-response_time']
    
    
class MentalHealthSummary(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mental_health_summary')
    assessment_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    summary = models.TextField()  # Summary of the user's mental health

    def __str__(self):
        return f"{self.user.username} - {self.assessment_date.strftime('%Y-%m-%d')}"

class MentalHealthSummaryHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mental_health_summary_histories')
    assessment_date = models.DateTimeField(auto_now_add=True)
    summary = models.TextField()

    def __str__(self):
        return f"History for {self.user.username} - {self.assessment_date.strftime('%Y-%m-%d')}"

class MentalHealthScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mental_health_scores')
    assessment_date = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Score for {self.user.username} - {self.score}"

class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    sender = models.CharField(max_length=10, choices=(('user', 'User'), ('bot', 'Bot')))

    def __str__(self):
        return f"{self.user.username} - {self.timestamp} - {self.sender}"


class MoodLog(models.Model):
    MOOD_CHOICES = [
        ('happy', 'Happy'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
        ('anxious', 'Anxious'),
        ('neutral', 'Neutral'),
        ('excited', 'Excited'),
        # Add more moods as needed
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mood = models.CharField(max_length=10, choices=MOOD_CHOICES)
    intensity = models.PositiveSmallIntegerField(help_text="Rate the intensity of your mood from 1 to 10")
    notes = models.TextField(blank=True, null=True, help_text="Any additional notes about your mood")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.mood} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    
# Existing models...

class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    suggested_by_ai = models.BooleanField(default=False)  # New field to identify AI suggested activities

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_date = models.DateField(null=True, blank=True)
    achieved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    suggested_by_ai = models.BooleanField(default=False)  # New field to identify AI suggested goals

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class JournalEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    entry_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.entry_date}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    

    
class UserPatternAndTrigger(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patterns_and_triggers')
    category = models.CharField(max_length=50)
    description = models.TextField() 
    severity = models.PositiveSmallIntegerField(help_text="Rate the severity (1 to 10)", null=True, blank=True) 
    identified_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.category} on {self.identified_date.strftime('%Y-%m-%d')}"   
    
    





   
   

