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
    system_instruction="You are a mental health analyzer. You should provide updates for activities, goals, mental health scores, and summaries based on the context given in the input. Output should be in the structured format as follows:\n"
                       "Mental Health Summary Update:\n[Updated summary text here]\n"
                       "Mental Health Score:\n[Score as a decimal value, e.g., 85.5 out of 100]\n"
                       "New Activities:\n- [Activity 1 title] (Optional description: [description])\n- [Activity 2 title] (Optional description: [description])\n- [Activity 3 title] (Optional description: [description])\n"
                       "New Goals:\n- [Goal 1 title] (Optional description: [description])\n- [Goal 2 title] (Optional description: [description])\n"
                       "Additional Notes:\n[Any additional notes or insights from the AI]\n"
)

@login_required
def analyze_and_update_session(request):
    user = request.user
    user_profile = user.profile
    current_datetime = datetime.datetime.now()
    
    # Fetch data for analysis
    journal_entries = JournalEntry.objects.filter(user=user).order_by('-entry_date')[:3]
    last_journal_entries_text = "\n".join([f"{entry.title}: {entry.content}" for entry in journal_entries])
    
    summary = get_object_or_404(MentalHealthSummary, user=user)
    mental_health_summary = summary.summary

    activities = Activity.objects.filter(user=user).order_by('-created_at')
    completed_activities = activities.filter(completed=True)[:3]
    pending_activities = activities.filter(completed=False)[:3]
    
    completed_activities_text = "\n".join([f"{activity.title} (Optional description: {activity.description})" for activity in completed_activities])
    pending_activities_text = "\n".join([f"{activity.title} (Optional description: {activity.description})" for activity in pending_activities])
    
    goals = Goal.objects.filter(user=user).order_by('-created_at')
    achieved_goals = goals.filter(achieved=True)[:3]
    pending_goals = goals.filter(achieved=False)[:3]
    
    achieved_goals_text = "\n".join([f"{goal.title} (Optional description: {goal.description})" for goal in achieved_goals])
    pending_goals_text = "\n".join([f"{goal.title} (Optional description: {goal.description})" for goal in pending_goals])
    
    mood_logs = MoodLog.objects.filter(user=user).order_by('-timestamp')[:3]
    last_mood_logs_text = "\n".join([f"{log.mood} (Intensity: {log.intensity}) - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}" for log in mood_logs])
    
    # Prepare the chat history for analysis
    chat_history = Chat.objects.filter(user=user).order_by('timestamp')
    chat_history_text = "\n".join([f"{chat.sender.capitalize()}: {chat.message}" for chat in chat_history])
    
    analysis_input = (
        f"User: {user.first_name} {user.last_name}, Age: {(datetime.date.today() - user_profile.date_of_birth).days // 365 if user_profile.date_of_birth else 'unknown'}, Date and Time: {current_datetime}.\n"
        f"Last 3 Journal Entries:\n{last_journal_entries_text}\n"
        f"Mental Health Summary:\n{mental_health_summary}\n"
        f"Last 3 Completed Activities:\n{completed_activities_text}\n"
        f"Pending Activities:\n{pending_activities_text}\n"
        f"Last 3 Achieved Goals:\n{achieved_goals_text}\n"
        f"Pending Goals:\n{pending_goals_text}\n"
        f"Last 3 Mood Logs:\n{last_mood_logs_text}\n"
        f"Chat History:\n{chat_history_text}\n"
        "Use this context to provide a thoughtful response to the user's queries."
    )

    chat_session = model.start_chat(
        history=[
            {
                "role": "system",
                "parts": [analysis_input],
            }
        ]
    )

    response = chat_session.send_message(analysis_input)
    response_text = response.text

    # Parsing the response
    summary_update = response_text.split("Mental Health Summary Update:")[1].split("Mental Health Score:")[0].strip()
    mental_health_score = float(response_text.split("Mental Health Score:")[1].split("New Activities:")[0].strip())

    new_activities = response_text.split("New Activities:")[1].split("New Goals:")[0].strip().split("\n")

    new_goals = response_text.split("New Goals:")[1].split("Pending Goals:")[0].strip().split("\n")
    # Process and insert the parsed data into models
    if summary_update:
        MentalHealthSummary.objects.update_or_create(user=user, defaults={'summary': summary_update})
        MentalHealthSummaryHistory.objects.create(user=user,summary=summary_update)

    if mental_health_score:
        MentalHealthScore.objects.create(user=user, score=mental_health_score)

    for activity_line in new_activities:
        if activity_line.strip():
            title, *desc = activity_line.split("(Optional description:")
            description = desc[0].replace(")", "").strip() if desc else None
            Activity.objects.create(user=user, title=title.strip(), description=description, suggested_by_ai=True)

    for goal_line in new_goals:
        if goal_line.strip():
            title, *desc = goal_line.split("(Optional description:")
            description = desc[0].replace(")", "").strip() if desc else None
            Goal.objects.create(user=user, title=title.strip(), description=description, suggested_by_ai=True)

    # Similarly, handle pending activities and goals if needed...

    return redirect('home')  # Redirect to a relevant view


