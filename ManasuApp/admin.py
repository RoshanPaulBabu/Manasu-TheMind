from django.contrib import admin
from .models import *

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
    list_filter = ('name',)

class UserResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'question','response_time')
    search_fields = ('user__username', 'question__text')
    list_filter = ('user', 'question', 'option', 'response_time')

class UserResponseHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'response_time')
    search_fields = ('user__username', 'question__text')
    list_filter = ('user', 'question', 'option', 'response_time')

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'mental_health_problem')
    search_fields = ('user__username', 'mental_health_problem__name')
    list_filter = ('gender', 'mental_health_problem')

@admin.register(MentalHealthSummary)
class MentalHealthSummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'assessment_date', 'last_updated')
    search_fields = ('user__username', 'assessment_date')
    list_filter = ('assessment_date',)

@admin.register(MentalHealthSummaryHistory)
class MentalHealthSummaryHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'assessment_date')
    search_fields = ('user__username', 'assessment_date')
    list_filter = ('assessment_date',)

@admin.register(MentalHealthScore)
class MentalHealthScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'assessment_date', 'score')
    search_fields = ('user__username', 'assessment_date')
    list_filter = ('assessment_date', 'score')

admin.site.register(MentalHealthProblem, MentalHealthProblemAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(UserResponse, UserResponseAdmin)
admin.site.register(UserResponseHistory, UserResponseHistoryAdmin)
admin.site.register(UserProfile, UserProfileAdmin)


admin.site.register(Chat)

@admin.register(MoodLog)
class MoodLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'mood', 'intensity', 'timestamp')
    search_fields = ('user__username', 'mood')
    list_filter = ('mood', 'timestamp')
    
    
@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'due_date', 'completed', 'created_at')
    search_fields = ('user__username', 'title')
    list_filter = ('completed', 'due_date', 'created_at')

@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'target_date', 'achieved', 'created_at')
    search_fields = ('user__username', 'title')
    list_filter = ('achieved', 'target_date', 'created_at')

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'entry_date', 'created_at')
    search_fields = ('user__username', 'title', 'entry_date')
    list_filter = ('entry_date', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'read', 'created_at')
    search_fields = ('user__username', 'message')
    list_filter = ('read', 'created_at')
