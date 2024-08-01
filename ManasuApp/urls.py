from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('', views.user_login, name='login'),
    path('home/', views.home, name='home'),
    path('questions/', views.questions, name='questions'),
    path('summary/', views.generate_summary, name='generate_summary'),
]
