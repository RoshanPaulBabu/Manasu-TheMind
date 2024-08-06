from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('', views.user_login, name='login'),
    path('home/', views.home, name='home'),
    path('questions/', views.questions, name='questions'),
    path('summary/', views.generate_summary, name='generate_summary'),
    path('logout/', views.user_logout, name='logout'),
    path('chat/', views.chat_with_ai, name='chat_with_ai'),
    path('analyze/', views.analyze_and_update_session, name='analyze_and_update_session'),
    path('log-mood/', views.log_mood, name='log_mood'),
    path('activities/', views.activities_view, name='activities_view'),
    path('goals/', views.goals_view, name='goals_view'),
    path('journal/', views.journal_entry_list, name='journal_entry_list'),
    path('journal/add/', views.journal_entry_create, name='journal_entry_create'),
    path('journal/<int:pk>/edit/', views.journal_entry_update, name='journal_entry_update'),
    path('journal/<int:pk>/delete/', views.journal_entry_delete, name='journal_entry_delete'),
]
