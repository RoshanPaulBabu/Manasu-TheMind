from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import *
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

User = get_user_model()

def register(request):
    if request.method == 'POST':
        full_name = request.POST.get('full-name')
        email = request.POST.get('your-email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')
        phone_number = request.POST.get('phone-number')
        address = request.POST.get('address')
        date_of_birth = request.POST.get('date-of-birth')
        gender = request.POST.get('gender')
        emergency_contact = request.POST.get('emergency-contact')
        emergency_contact_relationship = request.POST.get('emergency-contact-relationship')
        mental_health_problem_id = request.POST.get('mental-health-problem')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'registration/register.html')

        # Check password strength using Django's built-in validators
        try:
            if password:  # Ensure password is not None or empty
                validate_password(password)
        except ValidationError as e:
            messages.error(request, ', '.join(e.messages))
            return render(request, 'registration/register.html')

        try:
            mental_health_problem = MentalHealthProblem.objects.get(id=mental_health_problem_id)
        except MentalHealthProblem.DoesNotExist:
            messages.error(request, "Invalid mental health problem selected.")
            return redirect('register')

        # Validate phone number
        if not phone_number.isnumeric() or len(phone_number) < 10 or len(phone_number) > 15:
            messages.error(request, 'Phone number must be between 10 and 15 digits and contain only numbers.')
            return render(request, 'registration/register.html')

        # Check if the user already exists
        if User.objects.filter(username=email).exists():
            messages.error(request, 'A user with this email already exists.')
            return render(request, 'registration/register.html')

        # Create user
        try:
            user = User.objects.create_user(username=email, email=email, password=password)
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return render(request, 'registration/register.html')

        # Create user profile
        try:
            UserProfile.objects.create(
                user=user,
                phone_number=phone_number,
                address=address,
                date_of_birth=date_of_birth,
                gender=gender,
                emergency_contact=emergency_contact,
                emergency_contact_relationship=emergency_contact_relationship,
                mental_health_problem=mental_health_problem
            )
        except Exception as e:
            user.delete()  # Rollback user creation if profile creation fails
            messages.error(request, f'Error: {str(e)}')
            return render(request, 'registration/register.html')

        # Authenticate and login user
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Your account has been registered successfully!')
            return redirect('questions')  # Adjust this to your actual redirect target
        else:
            messages.error(request, 'Failed to login user.')
            return render(request, 'registration/register.html')

    mental_health_problems = MentalHealthProblem.objects.all()
    return render(request, 'registration/register.html', {'mental_health_problems': mental_health_problems})

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')  # Redirect to a home page or dashboard
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html')

def home(request):
    return render(request, 'home.html')


@login_required
def questions(request):
    user_profile = request.user.profile
    mental_health_problem = user_profile.mental_health_problem

    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('question_'):
                question_id = key.split('_')[1]
                question = get_object_or_404(Question, id=question_id)
                option = get_object_or_404(Option, id=value)
                UserResponse.objects.create(user=request.user, question=question, option=option)

        messages.success(request, 'Responses saved successfully.')
        return redirect('home')

    questions = Question.objects.filter(problem=mental_health_problem)
    return render(request, 'questions.html', {'questions': questions})

