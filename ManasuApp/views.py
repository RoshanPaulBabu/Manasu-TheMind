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
        first_name = request.POST.get('first-name')
        last_name = request.POST.get('last-name')
        email = request.POST.get('your-email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')
        phone_number = request.POST.get('phone-number')
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
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return render(request, 'registration/register.html')

        # Create user profile
        try:
            UserProfile.objects.create(
                user=user,
                phone_number=phone_number,
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
    problem = user_profile.mental_health_problem
    questions = problem.questions.all()

    if request.method == 'POST':
        for question in questions:
            if question.question_type == 'MC':
                option_id = request.POST.get(f'question_{question.id}')
                if option_id:
                    option = Option.objects.get(id=option_id)
                    
                    # Save to UserResponseHistory
                    UserResponseHistory.objects.create(
                        user=request.user,
                        question=question,
                        option=option
                    )
                    
                    # Update or create UserResponse
                    UserResponse.objects.update_or_create(
                        user=request.user,
                        question=question,
                        defaults={'option': option, 'open_ended_response': None}
                    )

            elif question.question_type == 'OE':
                response_text = request.POST.get(f'question_{question.id}')
                if response_text:
                    # Save to UserResponseHistory
                    UserResponseHistory.objects.create(
                        user=request.user,
                        question=question,
                        open_ended_response=response_text
                    )
                    
                    # Update or create UserResponse
                    UserResponse.objects.update_or_create(
                        user=request.user,
                        question=question,
                        defaults={'option': None, 'open_ended_response': response_text}
                    )
        
        return redirect('generate_summary')  # Redirect to a thank you page after submission

    context = {
        'problem': problem,
        'questions': questions,
    }
    return render(request, 'questions.html', context)



import os
import datetime
import google.generativeai as genai
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MentalHealthSummary, UserResponse, MentalHealthProblem

# Configure Google AI SDK
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Create the model with the system instruction
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="You are a mental health analyzer. You should make a summary of the user's mental health problem by analyzing the questions and answers responded by the user and other details like name, gender, and age.",
)

@login_required
def generate_summary(request):
    user_profile = request.user.profile
    mental_health_problem = user_profile.mental_health_problem

    if not mental_health_problem:
        messages.error(request, "Mental health problem not set for the user.")
        return redirect('home')

    # Fetch questions and responses
    responses = UserResponse.objects.filter(user=request.user, question__problem=mental_health_problem)

    # Aggregate responses
    questions_responses = []
    for response in responses:
        question_text = response.question.text
        if response.option:
            answer_text = response.option.text
        else:
            answer_text = response.open_ended_response
        
        questions_responses.append(f"Question: {question_text}\nAnswer: {answer_text}")

    questions_responses_text = "\n".join(questions_responses)

    # Prepare the input for the AI model
    name = f"{request.user.first_name} {request.user.last_name}"
    age = (datetime.date.today() - user_profile.date_of_birth).days // 365 if user_profile.date_of_birth else "unknown"
    gender = user_profile.gender if user_profile.gender else "unknown"
    summary_input = (
        f"User's name: {name}, Age: {age}, Gender: {gender}. Mental health problem: {mental_health_problem.name}.\n"
        f"Questions and Answers:\n{questions_responses_text}\n"
        "Based on this information, generate a detailed mental health summary and recommendations."
    )

    # Generate summary using the AI model
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [summary_input],
            }
        ]
    )

    response = chat_session.send_message(summary_input)

    # Save or update the mental health summary
    summary_obj, created = MentalHealthSummary.objects.update_or_create(
        user=request.user,
        defaults={
            'summary': response.text,
            'recommendations': "Consider consulting a mental health professional for further assessment and support."
        }
    )

    return render(request, 'summary.html', {'summary': summary_obj})

