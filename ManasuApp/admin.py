from django.contrib import admin
from .models import MentalHealthProblem, Question, Option, UserResponse, Chat, UserProfile

admin.site.register(MentalHealthProblem)
class OptionInline(admin.TabularInline):  # or admin.StackedInline
    model = Option
    extra = 1  # Number of empty forms to display by default
class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]

admin.site.register(Question, QuestionAdmin)    
admin.site.register(UserResponse)
admin.site.register(Chat)
admin.site.register(UserProfile)
