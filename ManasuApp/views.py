import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import *
from django.contrib.auth.decorators import login_required
import os
import datetime
import google.generativeai as genai
from django.utils import timezone
from django.utils.timezone import now

User = get_user_model()

def register(request):
    if request.method == 'POST':
        form_data = request.POST
        first_name = form_data.get('first-name')
        last_name = form_data.get('last-name')
        email = form_data.get('your-email')
        password = form_data.get('password')
        confirm_password = form_data.get('confirm-password')
        phone_number = form_data.get('phone-number')
        date_of_birth = form_data.get('date-of-birth')
        gender = form_data.get('gender')
        emergency_contact = form_data.get('emergency-contact')
        emergency_contact_relationship = form_data.get('emergency-contact-relationship')
        mental_health_problem_id = form_data.get('mental-health-problem')

        # Validate password
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'registration/register.html')

        try:
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
        if not phone_number.isnumeric() or not (10 <= len(phone_number) <= 15):
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
            UserProfile.objects.create(
                user=user,
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                gender=gender,
                emergency_contact=emergency_contact,
                emergency_contact_relationship=emergency_contact_relationship,
                mental_health_problem=mental_health_problem
            )
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Your account has been registered successfully!')
                # Redirect based on the selected mental health problem
                if mental_health_problem.name == 'Other':  # assuming the "name" field contains the problem name
                    return redirect('chat_with_ai')
                else:
                    return redirect('questions')
        except Exception as e:
            if user:
                user.delete()
            messages.error(request, f'Error: {str(e)}')
            return render(request, 'registration/register.html')

    mental_health_problems = MentalHealthProblem.objects.all()
    return render(request, 'registration/register.html', {'mental_health_problems': mental_health_problems})



#User login view
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

#user logout view
def user_logout(request):
    logout(request)
    return redirect('/') 


#dashboard view
import json
@login_required
def home(request):
    # Fetch the 2 most recent journal entries for the logged-in user
    entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')[:2]
    
    # Fetch the mood log for the current day
    today = now().date()
    mood_log = MoodLog.objects.filter(user=request.user, timestamp__date=today).first()
    
    mood = mood_log.mood if mood_log else 'No mood logged'
    intensity = mood_log.intensity if mood_log else 'N/A'
    notes = mood_log.notes if mood_log else 'No additional notes'

    # Determine if the mood log form should be shown based on the 5-hour restriction
    last_mood_log = MoodLog.objects.filter(user=request.user).order_by('-timestamp').first()
    can_log_mood = False
    if not last_mood_log or (now() - last_mood_log.timestamp >= timedelta(hours=5)):
        can_log_mood = True
    
    # Fetch activities
    total_activities = Activity.objects.filter(user=request.user).count()
    completed_activities = Activity.objects.filter(user=request.user, completed=True).count()
    
    # Fetch goals
    total_goals = Goal.objects.filter(user=request.user).count()
    achieved_goals = Goal.objects.filter(user=request.user, achieved=True).count()
    
    # Calculate percentage of goals achieved
    goal_percentage = (achieved_goals / total_goals * 100) if total_goals > 0 else 0

    # Fetch mental health scores for the past week
    past_week = [today - timedelta(days=i) for i in range(7)]
    mental_health_scores = MentalHealthScore.objects.filter(user=request.user, assessment_date__date__in=past_week).order_by('assessment_date')

    # Create a dictionary with dates as keys and scores as values
    scores_dict = {score.assessment_date.date(): float(score.score) for score in mental_health_scores}
    scores_list = [scores_dict.get(day, 0) for day in past_week]  # Default to 0 if no score for the day

    # Format the dates for the past week
    dates_list = [day.strftime("%Y-%m-%d") for day in past_week]

    context = {
        'entries': entries,
        'mood': mood,
        'intensity': intensity,
        'notes': notes,
        'completed_activities': completed_activities,
        'total_activities': total_activities,
        'goal_percentage': goal_percentage,
        'mental_health_scores': json.dumps(scores_list[::-1]),  # Pass data in reverse order to match the labels
        'dates_list': json.dumps(dates_list[::-1]),  # Pass dates in reverse order
        'can_log_mood': can_log_mood,  # Control whether to show the mood form
    }
    
    return render(request, 'home.html', context)

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
                    UserResponseHistory.objects.create(
                        user=request.user,
                        question=question,
                        option=option
                    )
                    UserResponse.objects.update_or_create(
                        user=request.user,
                        question=question,
                        defaults={'option': option, 'open_ended_response': None}
                    )
            elif question.question_type == 'OE':
                response_text = request.POST.get(f'question_{question.id}')
                if response_text:
                    UserResponseHistory.objects.create(
                        user=request.user,
                        question=question,
                        open_ended_response=response_text
                    )
                    UserResponse.objects.update_or_create(
                        user=request.user,
                        question=question,
                        defaults={'option': None, 'open_ended_response': response_text}
                    )
        return redirect('generate_summary')

    context = {
        'problem': problem,
        'questions': questions,
    }
    return render(request, 'questions.html', context)




# Configure Google AI SDK
genai.configure(api_key="AIzaSyAYVSrCaSRTgMRk_jdEvXyrTuejMKn3i58")


# AI model configuration for the summary generationns
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
    system_instruction = "You are a mental health chatbot providing empathetic and practical support based on recent activities, mood logs, and other user data. Engage with users to understand their experiences and factors contributing to their current state. Offer actionable tips and strategies to improve their mental well-being. Aim to gather sufficient data to determine the user's mental health condition and provide a score out of 100,Ensure the chat is short and concise, if its long give in points",

)

@login_required
def chat_with_ai(request):
    user = request.user

    if not request.session.get('interaction_count'):
        request.session['interaction_count'] = 0

    print(f"Initial interaction count: {request.session['interaction_count']}")

    # Fetch the last 15 chat messages for the current user
    chat_history = Chat.objects.filter(user=user).order_by('-timestamp')[:15]

    # Format the chat history for the AI model
    formatted_history = []
    for chat in reversed(chat_history):
        role = 'user' if chat.sender == 'user' else 'model'
        if chat.message.strip():  # Ensure message is not empty
            formatted_history.append({
                "role": role,
                "parts": [chat.message],
            })

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

    # System prompt for the AI model
    system_prompt = (
        f"User: {user.first_name} {user.last_name}, Age: {age}, Date and Time: {current_datetime}.\n"
        f"Last 3 Journal Entries:\n{last_journal_entries_text}\n"
        f"Mental Health Summary:\n{mental_health_summary}\n"
        f"Last 3 Completed Activities:\n{completed_activities_text}\n"
        f"Pending Activities:\n{pending_activities_text}\n"
        f"Last 3 Achieved Goals:\n{achieved_goals_text}\n"
        f"Pending Goals:\n{pending_goals_text}\n"
        f"Last 3 Mood Logs:\n{last_mood_logs_text}\n"
        "Use this context to provide a thoughtful response to the user's queries."
    ).strip()
    
    if request.method == 'POST':
        user_message = request.POST.get('message', '').strip()
        
        if not user_message:
            return render(request, 'chat.html', {
                'error': 'Please enter a message.',
                'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
            })

        # Ensure system_prompt and formatted_history are not empty
        if not system_prompt and not formatted_history:
            return render(request, 'chat.html', {
                'error': 'Unable to process request due to missing context.',
                'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
            })

        try:
            # Start a chat session with AI
            chat_session = chatbot_model.start_chat(
                history=[
                    {
                        "role": "model",
                        "parts": [system_prompt],
                    } if system_prompt else None,
                    *formatted_history,
                    {
                        "role": "user",
                        "parts": [user_message],
                    }
                ]
            )

            request.session['interaction_count'] += 1
            print(f"Updated interaction count: {request.session['interaction_count']}")

            # Check if the interaction count has reached the thresholdddd
            if request.session['interaction_count'] >= 6:  # Example threshold
                # Reset the counter
                request.session['interaction_count'] = 0
                print("Interaction count threshold reached. Triggering analyze_and_update_session view.")
                # Trigger the analyze_and_update_session vdiews
                return analyze_and_update_session(request)

            ai_response = chat_session.send_message(user_message)
            ai_text = ai_response.text

            # Save chat history
            Chat.objects.create(user=user, message=user_message, sender='user')
            Chat.objects.create(user=user, message=ai_text, sender='bot')

            # # Check if AI response includes the trigger
            # if "[analyze_and_update_session]" in ai_text:
            #     print("Trigger found in AI response. Redirecting to analyze_and_update_session view.")
            #     return redirect('analyze_and_update_session')

            return render(request, 'chat.html', {
                'response': ai_text,
                'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
            })

        except ValueError as e:
            return render(request, 'chat.html', {
                'error': f"An error occurred: {str(e)}",
                'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
            })

    return render(request, 'chat.html', {
        'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
    })



# AI model configuration for the summary generation
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 11192,
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config=generation_config,
    system_instruction="You are a mental health analyzer. Provide updates for activities, goals, mental health scores, and summaries based on the context given in the input, Dont repeat anything such as goals or actvities. Output should be in the following JSON format:\n"
                       "{\n"
                       "  \"mental_health_summary\": \"[Updated summary text here]\",\n"
                       "  \"mental_health_score\": [Score as a decimal value out of 100, e.g., 85.5],\n"
                       "  \"new_goals\": [\n"
                       "    {\"title\": \"[Goal 1 title]\", \"description\": \"[description]\"},\n"
                       "    {\"title\": \"[Goal 2 title]\", \"description\": \"[description]\"}\n"
                       "  ]\n"
                       "  \"new_activities\": [\n"
                       "    {\"title\": \"[Activity 1 title]\", \"description\": \"[description]\"},\n"
                       "    {\"title\": \"[Activity 2 title]\", \"description\": \"[description]\"},\n"
                       "    {\"title\": \"[Activity 3 title]\", \"description\": \"[description]\"}\n"
                       "  ],\n"
                       "}"
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

    completed_activities_text = "\n".join([f"{activity.title} (description: {activity.description})" for activity in completed_activities])
    pending_activities_text = "\n".join([f"{activity.title} (description: {activity.description})" for activity in pending_activities])

    goals = Goal.objects.filter(user=user).order_by('-created_at')
    achieved_goals = goals.filter(achieved=True)[:3]
    pending_goals = goals.filter(achieved=False)[:3]

    achieved_goals_text = "\n".join([f"{goal.title} (description: {goal.description})" for goal in achieved_goals])
    pending_goals_text = "\n".join([f"{goal.title} (description: {goal.description})" for goal in pending_goals])

    mood_logs = MoodLog.objects.filter(user=user).order_by('-timestamp')[:3]
    last_mood_logs_text = "\n".join([f"{log.mood} (Intensity: {log.intensity}) - {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}" for log in mood_logs])

    # Prepare the chat history for analysis
    chat_history = Chat.objects.filter(user=user).order_by('timestamp')[:20]
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
                "role": "model",
                "parts": [analysis_input],
            }
        ]
    )

    response = chat_session.send_message(analysis_input)
    response_text = response.text
    
    print(response_text)

    # Parsing the JSON response
    response_data = json.loads(response_text)

    summary_update = response_data.get("mental_health_summary", "")
    mental_health_score = response_data.get("mental_health_score", 0.0)
    new_activities = response_data.get("new_activities", [])
    new_goals = response_data.get("new_goals", [])

    # Process and insert the parsed data into models
    if summary_update:
        MentalHealthSummary.objects.update_or_create(user=user, defaults={'summary': summary_update})
        MentalHealthSummaryHistory.objects.create(user=user, summary=summary_update)

    if mental_health_score:
        MentalHealthScore.objects.create(user=user, score=mental_health_score)

    for activity in new_activities:
        title = activity.get("title", "")
        description = activity.get("description", "")
        if title:
            Activity.objects.create(user=user, title=title, description=description, suggested_by_ai=True)

    for goal in new_goals:
        title = goal.get("title", "")
        description = goal.get("description", "")
        if title:
            Goal.objects.create(user=user, title=title, description=description, suggested_by_ai=True)

    return redirect('home')  # Redirect to a relevant view

from django.http import JsonResponse

from django.utils.timezone import now, timedelta

@login_required
def log_mood(request):
    if request.method == 'POST':
        mood = request.POST.get('mood')
        intensity = request.POST.get('intensity')
        notes = request.POST.get('notes')

        # Create a new MoodLog entry
        mood_log = MoodLog(
            user=request.user,
            mood=mood,
            intensity=intensity,
            notes=notes
        )
        mood_log.save()

        # Redirect to the home page after logging the mood
        return redirect('home')
    
    return render(request, 'log_mood.html')

from .forms import ActivityForm, GoalForm, JournalEntryForm

from django.shortcuts import render, get_object_or_404, redirect
from .models import Activity
from .forms import ActivityForm

def activities_view(request):
    user_activities = Activity.objects.filter(user=request.user, suggested_by_ai=False)
    ai_suggested_activities = Activity.objects.filter(user=request.user, suggested_by_ai=True)

    # Initialize forms
    form = ActivityForm()
    edit_form = ActivityForm()  # Will be populated with specific activity data later
    delete_activity_id = None  # Will hold the ID of the activity to be deleted

    if request.method == "POST":
        if 'add_activity' in request.POST:
            form = ActivityForm(request.POST)
            if form.is_valid():
                new_activity = form.save(commit=False)
                new_activity.user = request.user
                new_activity.save()
                return redirect('activities_view')
        elif 'edit_activity' in request.POST:
            activity_id = request.POST.get('activity_id')
            activity = get_object_or_404(Activity, id=activity_id, user=request.user)
            edit_form = ActivityForm(request.POST, instance=activity)
            if edit_form.is_valid():
                edit_form.save()
                return redirect('activities_view')
        elif 'delete_activity' in request.POST:
            delete_activity_id = request.POST.get('activity_id')
            activity = get_object_or_404(Activity, id=delete_activity_id, user=request.user)
            activity.delete()
            return redirect('activities_view')
        elif 'move_to_regular' in request.POST:
            activity_id = request.POST.get('activity_id')
            activity = get_object_or_404(Activity, id=activity_id, user=request.user)
            activity.suggested_by_ai = False
            activity.save()
            return redirect('activities_view')

    context = {
        'user_activities': user_activities,
        'ai_suggested_activities': ai_suggested_activities,
        'form': form,
        'edit_form': edit_form,
        'delete_activity_id': delete_activity_id,
    }

    return render(request, 'activities.html', context)





def goals_view(request):
    user_goals = Goal.objects.filter(user=request.user, suggested_by_ai=False)
    ai_suggested_goals = Goal.objects.filter(user=request.user, suggested_by_ai=True)

    # Initialize forms
    form = GoalForm()
    edit_form = GoalForm()  # Will be populated with specific goal data later
    delete_goal_id = None  # Will hold the ID of the goal to be deleted

    if request.method == "POST":
        if 'add_goal' in request.POST:
            form = GoalForm(request.POST)
            if form.is_valid():
                new_goal = form.save(commit=False)
                new_goal.user = request.user
                new_goal.save()
                return redirect('goals_view')
        elif 'edit_goal' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = get_object_or_404(Goal, id=goal_id, user=request.user)
            edit_form = GoalForm(request.POST, instance=goal)
            if edit_form.is_valid():
                edit_form.save()
                return redirect('goals_view')
        elif 'delete_goal' in request.POST:
            delete_goal_id = request.POST.get('goal_id')
            goal = get_object_or_404(Goal, id=delete_goal_id, user=request.user)
            goal.delete()
            return redirect('goals_view')
        elif 'move_to_regular' in request.POST:
            goal_id = request.POST.get('goal_id')
            goal = get_object_or_404(Goal, id=goal_id, user=request.user)
            goal.suggested_by_ai = False
            goal.save()
            return redirect('goals_view')

    context = {
        'user_goals': user_goals,
        'ai_suggested_goals': ai_suggested_goals,
        'form': form,
        'edit_form': edit_form,
        'delete_goal_id': delete_goal_id,
    }

    return render(request, 'goals.html', context)


@login_required
def journal_entry_list(request):
    entries = JournalEntry.objects.filter(user=request.user).order_by('-entry_date')
    return render(request, 'journal_entry_list.html', {'entries': entries})

@login_required
def journal_entry_create(request):
    if request.method == 'POST':
        form = JournalEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            return redirect('journal_entry_list')
    else:
        form = JournalEntryForm()
    return render(request, 'journal_entry_form.html', {'form': form})

@login_required
def journal_entry_update(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        form = JournalEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            return redirect('journal_entry_list')
    else:
        form = JournalEntryForm(instance=entry)
    return render(request, 'journal_entry_form.html', {'form': form})

@login_required
def journal_entry_delete(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.delete()
        return redirect('journal_entry_list')
    return render(request, 'journal_entry_confirm_delete.html', {'entry': entry})


# @login_required
# def chat_with_ai(request):
#     user = request.user

#     if not request.session.get('interaction_count'):
#         request.session['interaction_count'] = 0

#     print(f"Initial interaction count: {request.session['interaction_count']}")

#     # Fetch the last 15 chat messages for the current user
#     chat_history = Chat.objects.filter(user=user).order_by('-timestamp')[:15]

#     # Format the chat history for the AI model
#     formatted_history = []
#     for chat in reversed(chat_history):
#         role = 'user' if chat.sender == 'user' else 'model'
#         if chat.message.strip():  # Ensure message is not empty
#             formatted_history.append({
#                 "role": role,
#                 "parts": [chat.message],
#             })

#         # Gather the last 3 journal entries
#     last_journal_entries = JournalEntry.objects.filter(user=user).order_by('-created_at')[:3]
#     last_journal_entries_text = "\n".join([f"{entry.title}: {entry.content}" for entry in last_journal_entries])

#     # Get the latest mental health summary
#     try:
#         mental_health_summary = user.mental_health_summary.summary
#     except MentalHealthSummary.DoesNotExist:
#         mental_health_summary = "No summary available."

#     # Gather the last 3 completed activities and 3 pending activities
#     completed_activities = Activity.objects.filter(user=user, completed=True).order_by('-created_at')[:3]
#     pending_activities = Activity.objects.filter(user=user, completed=False).order_by('-created_at')[:3]

#     completed_activities_text = "\n".join([activity.title for activity in completed_activities])
#     pending_activities_text = "\n".join([activity.title for activity in pending_activities])

#     # Gather the last 3 achieved goals and 3 pending goals
#     achieved_goals = Goal.objects.filter(user=user, achieved=True).order_by('-created_at')[:3]
#     pending_goals = Goal.objects.filter(user=user, achieved=False).order_by('-created_at')[:3]

#     achieved_goals_text = "\n".join([goal.title for goal in achieved_goals])
#     pending_goals_text = "\n".join([goal.title for goal in pending_goals])

#     # Gather the last 3 mood logs
#     last_mood_logs = MoodLog.objects.filter(user=user).order_by('-timestamp')[:3]
#     last_mood_logs_text = "\n".join([f"{log.mood}: {log.intensity}/10" for log in last_mood_logs])

#     # Prepare the chat context
#     current_datetime = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
#     age = (timezone.now().date() - user.profile.date_of_birth).days // 365 if user.profile.date_of_birth else "unknown"

#     # System prompt for the AI model
#     system_prompt = (
#         f"User: {user.first_name} {user.last_name}, Age: {age}, Date and Time: {current_datetime}.\n"
#         f"Last 3 Journal Entries:\n{last_journal_entries_text}\n"
#         f"Mental Health Summary:\n{mental_health_summary}\n"
#         f"Last 3 Completed Activities:\n{completed_activities_text}\n"
#         f"Pending Activities:\n{pending_activities_text}\n"
#         f"Last 3 Achieved Goals:\n{achieved_goals_text}\n"
#         f"Pending Goals:\n{pending_goals_text}\n"
#         f"Last 3 Mood Logs:\n{last_mood_logs_text}\n"
#         "Use this context to provide a thoughtful response to the user's queries."
#     ).strip()
    
#     print(system_prompt)

#     if request.method == 'POST':
#         user_message = request.POST.get('message', '').strip()
        
#         if not user_message:
#             return render(request, 'chat.html', {
#                 'error': 'Please enter a message.',
#                 'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
#             })

#         # Ensure system_prompt and formatted_history are not empty
#         if not system_prompt and not formatted_history:
#             return render(request, 'chat.html', {
#                 'error': 'Unable to process request due to missing context.',
#                 'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
#             })

#         try:
#             # Start a chat session with AI
#             chat_session = chatbot_model.start_chat(
#                 history=[
#                     {
#                         "role": "model",
#                         "parts": [system_prompt],
#                     } if system_prompt else None,
#                     *formatted_history,
#                     {
#                         "role": "user",
#                         "parts": [user_message],
#                     }
#                 ]
#             )

#             request.session['interaction_count'] += 1
#             print(f"Updated interaction count: {request.session['interaction_count']}")

#             # Check if the interaction count has reached the threshold
#             if request.session['interaction_count'] >= 20:  # Example threshold
#                 # Reset the counter
#                 request.session['interaction_count'] = 0
#                 print("Interaction count threshold reached. Triggering analyze_and_update_session view.")
#                 # Trigger the analyze_and_update_session view
#                 return analyze_and_update_session(request)

#             ai_response = chat_session.send_message(user_message)
#             ai_text = ai_response.text

#             # Save chat history
#             Chat.objects.create(user=user, message=user_message, sender='user')
#             Chat.objects.create(user=user, message=ai_text, sender='bot')

#             # # Check if AI response includes the trigger
#             # if "[analyze_and_update_session]" in ai_text:
#             #     print("Trigger found in AI response. Redirecting to analyze_and_update_session view.")
#             #     return redirect('analyze_and_update_session')

#             return render(request, 'chat.html', {
#                 'response': ai_text,
#                 'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
#             })

#         except ValueError as e:
#             return render(request, 'chat.html', {
#                 'error': f"An error occurred: {str(e)}",
#                 'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
#             })

#     return render(request, 'chat.html', {
#         'chat_history': Chat.objects.filter(user=user).order_by('timestamp')
#     })

