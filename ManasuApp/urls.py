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
]
