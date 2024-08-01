from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

class MentalHealthProblem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class Question(models.Model):
    problem = models.ForeignKey(MentalHealthProblem, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()

    def __str__(self):
        return f"{self.problem.name} - {self.text[:50]}"

class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    value = models.IntegerField()

    def __str__(self):
        return f"{self.question.text[:50]} - {self.text}"

class UserResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    option = models.ForeignKey(Option, on_delete=models.CASCADE)
    response_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.question.text[:50]}"

class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    sender = models.CharField(max_length=10, choices=(('user', 'User'), ('bot', 'Bot')))

    def __str__(self):
        return f"{self.user.username} - {self.timestamp} - {self.sender}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=(('male', 'Male'), ('female', 'Female'), ('other', 'Other')), blank=True)
    emergency_contact = models.CharField(max_length=15, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)
    mental_health_problem = models.ForeignKey(MentalHealthProblem, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')


    def __str__(self):
        return self.user.username
    
    
class MentalHealthSummary(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mental_health_summary')
    assessment_date = models.DateTimeField(auto_now_add=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # To store overall score
    summary = models.TextField()  # Summary of the user's mental health
    recommendations = models.TextField()  # Recommendations for the user based on their responses

    def __str__(self):
        return f"{self.user.username} - {self.assessment_date.strftime('%Y-%m-%d')}"




   