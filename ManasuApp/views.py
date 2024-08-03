from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, get_user_model, logout
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
            messages.success(request, f'Welcome back, {request.user.first_name} {request.user.last_name}!')
            return redirect('home')  # Redirect to a home page or dashboard
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'registration/login.html')

def user_logout(request):
    logout(request)
    return redirect('/') 

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
from django.utils import timezone

# Configure Google AI SDK
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))


# AI model configuration for the summary generation
summary_generation_config = {
    "temperature": 0.7,
    "top_p": 0.85,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

summary_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=summary_generation_config,
    system_instruction="You are a mental health analyst. Generate a detailed report based on the user's mental health data",
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
        "Based on this information, generate a detailed mental health report."
    )

    # Generate summary using the AI model
    chat_session = summary_model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [summary_input],
            }
        ]
    )

    response = chat_session.send_message(summary_input)

    # Save the new summary to history
    MentalHealthSummaryHistory.objects.create(
        user=request.user,
        summary=response.text
    )

    # Update or create the current mental health summary
    summary_obj, created = MentalHealthSummary.objects.update_or_create(
        user=request.user,
        defaults={
            'summary': response.text
        }
    )

    return render(request, 'summary.html', {'summary': summary_obj})


# AI model configuration for the chatbot
chatbot_generation_config = {
    "temperature": 1,
    "top_p": 0.9,
    "top_k": 50,
    "max_output_tokens": 4096,
    "response_mime_type": "text/plain",
}

chatbot_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=chatbot_generation_config,
    system_instruction="You are a mental health chatbot that provides empathetic and practical support to users based on their recent activities and mood logs.",
)

@login_required
def chat_with_ai(request):
    user = request.user

    # Gather the last 3 journal entries
    last_journal_entries = JournalEntry.objects.filter(user=user).order_by('-created_at')[:3]
    last_journal_entries_text = "\n".join([f"{entry.title}: {entry.content}" for entry in last_journal_entries])

    # Get the latest mental health summary
    try:
        mental_health_summary = user.mental_health_summary.summary
    except MentalHealthSummary.DoesNotExist:
        mental_health_summary = "No summary available."

    # Gather the last 3 completed activities and 3 pending activities
    completed_activities = Activity.objects.filter(user=user, completed=True).order_by('-created_at')[:3]
    pending_activities = Activity.objects.filter(user=user, completed=False).order_by('-created_at')[:3]

    completed_activities_text = "\n".join([activity.title for activity in completed_activities])
    pending_activities_text = "\n".join([activity.title for activity in pending_activities])

    # Gather the last 3 achieved goals and 3 pending goals
    achieved_goals = Goal.objects.filter(user=user, achieved=True).order_by('-created_at')[:3]
    pending_goals = Goal.objects.filter(user=user, achieved=False).order_by('-created_at')[:3]

    achieved_goals_text = "\n".join([goal.title for goal in achieved_goals])
    pending_goals_text = "\n".join([goal.title for goal in pending_goals])

    # Gather the last 3 mood logs
    last_mood_logs = MoodLog.objects.filter(user=user).order_by('-timestamp')[:3]
    last_mood_logs_text = "\n".join([f"{log.mood}: {log.intensity}/10" for log in last_mood_logs])

    # Prepare the chat context
    current_datetime = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    age = (timezone.now().date() - user.profile.date_of_birth).days // 365 if user.profile.date_of_birth else "unknown"
    user_name = user.username

    # System prompt for the AI model
    system_prompt = (
        f"User: {user_name}, Age: {age}, Date and Time: {current_datetime}.\n"
        f"Last 3 Journal Entries:\n{last_journal_entries_text}\n"
        f"Mental Health Summary:\n{mental_health_summary}\n"
        f"Last 3 Completed Activities:\n{completed_activities_text}\n"
        f"Pending Activities:\n{pending_activities_text}\n"
        f"Last 3 Achieved Goals:\n{achieved_goals_text}\n"
        f"Pending Goals:\n{pending_goals_text}\n"
        f"Last 3 Mood Logs:\n{last_mood_logs_text}\n"
        "Use this context to provide a thoughtful response to the user's queries."
    )

    if request.method == 'POST':
        user_message = request.POST.get('message')

        # Start a chat session with AI
        chat_session = chatbot_model.start_chat(
            history=[
                {
                    "role": "model",
                    "parts": [system_prompt],
                },
                {
                    "role": "user",
                    "parts": [user_message],
                }
            ]
        )

        ai_response = chat_session.send_message(user_message)

        # Save chat history
        Chat.objects.create(user=user, message=user_message, sender='user')
        Chat.objects.create(user=user, message=ai_response.text, sender='bot')

        return render(request, 'chat.html', {'response': ai_response.text})

    return render(request, 'chat.html')


