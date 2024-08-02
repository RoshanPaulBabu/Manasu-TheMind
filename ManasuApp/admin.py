from django.contrib import admin
from .models import MentalHealthProblem, Question, Option, UserResponse, UserResponseHistory, UserProfile

class OptionInline(admin.TabularInline):
    model = Option
    extra = 1

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ('text', 'question_type', 'problem')
    search_fields = ('text',)
    list_filter = ('question_type', 'problem')

class MentalHealthProblemAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

class UserResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'option', 'open_ended_response', 'response_time')
    search_fields = ('user__username', 'question__text')
    list_filter = ('user', 'question', 'option', 'response_time')

class UserResponseHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'option', 'open_ended_response', 'response_time')
    search_fields = ('user__username', 'question__text')
    list_filter = ('user', 'question', 'option', 'response_time')

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'email', 'date_of_birth', 'gender', 'emergency_contact', 'emergency_contact_relationship', 'mental_health_problem')
    search_fields = ('user__username', 'mental_health_problem__name')
    list_filter = ('gender', 'mental_health_problem')

admin.site.register(MentalHealthProblem, MentalHealthProblemAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(UserResponse, UserResponseAdmin)
admin.site.register(UserResponseHistory, UserResponseHistoryAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
