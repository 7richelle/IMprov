from django.shortcuts import render, redirect
from django.contrib import messages
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
#CHANGED
import json
import requests
from django.http import JsonResponse
from urllib.parse import unquote
import os, json, datetime
from django.utils import timezone
from django.contrib.auth.models import User
import random
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from .models import PasswordResetOTP
from .forms import ForgotPasswordForm, OTPVerificationForm, ResetPasswordForm
from django.contrib.auth.hashers import make_password, check_password  # ✅ ADD THIS

# --- SUPABASE CONFIG ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


#  REGISTER FUNCTION
def register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        #  Check if email already exists in 'user' table
        check_user = supabase.table("user").select("*").eq("email", email).execute()

        if check_user.data:
            messages.warning(request, "Account already exists. Please log in instead.")
            return render(request, "register.html")


        #  Insert new user
        data = {
            "name": name,
            "email": email,
            "password": password,  # store as plain text (varchar) 
        }

        response = supabase.table("user").insert(data).execute()

        print(" Supabase Insert Response:", response)

        if response.data:
            messages.success(request, "Registration successful! You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "Something went wrong while saving your account.")
            return render(request, "register.html")

    return render(request, "register.html")


#  LOGIN FUNCTION
def login_user(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # 🔍 Fetch user by email
        response = supabase.table("user").select("*").eq("email", email).execute()

        if response.data:
            user = response.data[0]
            stored_password = user["password"]

            #  Check plain password (no hashing)
            if password == stored_password:
                #  Login success
                request.session["user_email"] = user["email"]
                request.session["user_name"] = user["name"]
                request.session["user_id"] = user["user_id"]
                #ADMIN
                request.session["is_staff"] = user.get("is_staff", False)
                request.session["is_superuser"] = user.get("is_superuser", False)

                messages.success(request, f"Welcome back, {user['name']}!")

                if user.get("is_superuser") or user.get("is_staff"):
                    return redirect("admin_dashboard")
                else:
                    return redirect("task_dashboard")
            else:
                #  Wrong password
                messages.error(request, "Incorrect password. Please try again.")
                return render(request, "login.html")
        else:
            #  No user found
            #messages.error(request, "Email not registered.")
            return render(request, "login.html")

    # Default (GET request)
    return render(request, "login.html")




@csrf_exempt
def generate_task(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            task_type = data.get("type")
            difficulty = data.get("difficulty")
            frequency = data.get("frequency")
            duration = data.get("duration")
            user_email = data.get("email")

            #  AI prompt
            prompt = (
                 f"Generate one unique {task_type} productivity task that matches these details:\n"
    f"- Difficulty: {difficulty}\n"
    f"- Duration: {duration}\n"
    f"- Frequency: {frequency}\n"
    f"- Task type: {task_type} (Active = movement, exercise, or cleaning. Stationary = reading, writing, organizing, or creative focus.)\n\n"
    
    f"The task must:\n"
    f"1. Be realistic and doable for that difficulty level and duration.\n"
    f"2. Match the type — if it's active, make it physical (e.g., walking, stretching, chores, exercise). "
    f"If it's stationary, make it calm or focus-based (e.g., reading, writing, organizing desk, doing creative work).\n"
    f"3. Speak directly to the user (use 'you').\n"
    f"4. Be short, specific, and easy to understand — 1 to 2 sentences only.\n"
    f"5. Avoid journaling, meditation, or emotional reflection.\n"
    f"6. Make each generation unique by varying the activity, not reusing old patterns.\n\n"
    
    f"After the task, add one short line starting with 'Why it helps:' or 'Why it works:' that gives a quick motivational reason."
    f"Add one short line explaining why it's helpful or satisfying."
            )

            #  Load OpenRouter API key securely
            OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

            # 🛰 Send request to OpenRouter
            response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "nvidia/nemotron-nano-9b-v2:free",
        "messages": [
            {"role": "system", "content": "You are a helpful productivity coach."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,  # controls randomness: 0=deterministic, 1=very creative
        "top_p": 0.9          # optional, adds extra variation
    },
)


            ai_result = response.json()
            if response.status_code != 200 or "choices" not in ai_result:
              print(" OpenRouter error:", ai_result)
              return JsonResponse({
                 "success": False,
                 "error": ai_result.get("error", ai_result)
             })


            #  Extract generated text
            generated_task = ai_result["choices"][0]["message"]["content"].strip()

            #  Extract generated text
            generated_task = ai_result["choices"][0]["message"]["content"].strip()

            #  Save to Supabase "task" table
            user_id = request.session.get("user_id")  # <-- add this line
            task_data = {
                "user_id": user_id, 
                "task_type": task_type,
                "difficulty": difficulty,
                "frequency": frequency,
                "duration": duration,
                "description": generated_task,
                "status": "not started",
            }

            insert_response = supabase.table("task").insert(task_data).execute()
            print("🪄 Task saved:", insert_response)

            return JsonResponse({
                "success": True,
                "generated_task": generated_task,
                "task_id": insert_response.data[0]["task_id"] if insert_response.data else None
            })

        except Exception as e:
            print(" Error generating task:", e)
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"error": "Invalid request method"}, status=400)

def task_dashboard(request):
    # Ensure only logged-in users can access the dashboard
    if "user_email" not in request.session or "user_id" not in request.session:
        messages.warning(request, "Please log in first.")
        return redirect("login")

    user_email = request.session["user_email"]
    user_name = request.session["user_name"]
    user_id = request.session["user_id"]  # safe now

    return render(
        request,
        "task_dashboard.html",
        {
            "user_name": user_name,
            "user_email": user_email,
            "user_id": user_id,
        },
    )

#CHANGED
def task_frequency(request):
    return render(request, "task_frequency.html")


def task_duration(request):
    # get data from previous selections
    task_type = request.GET.get('type')
    difficulty = request.GET.get('difficulty')
    frequency = request.GET.get('frequency')

    if request.method == 'POST':
        duration = request.POST.get('duration')

        #  Example: generate a simple task description (you can replace this with your AI call later)
        generated_task = f"A {difficulty} {task_type} task for {duration} minutes ({frequency} frequency)."

        #  Redirect to the result page, passing the generated task as a query parameter
        return redirect(f'/result/?task={generated_task}')

    # if not POST, just show the duration selection page
    return render(request, "task_duration.html")

def task_result(request):
    task_param = request.GET.get("task", "")
    duration = request.GET.get("duration")
    generated_task = unquote(task_param)
    task_id = request.GET.get("task_id")  # add this line

    return render(request, "task_result.html", {
        "generated_task": generated_task,
        "duration": duration,  
        "task_id": task_id,  # pass it to template
        })


#  Start a task session
@csrf_exempt
def start_task_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            task_id = data.get("task_id")
            user_id = request.session.get("user_id")  # get from session

            if not user_id or not task_id:
                return JsonResponse({"success": False, "error": "Missing user or task ID"})

            start_time = timezone.localtime(timezone.now()).isoformat()

            response = supabase.table("tasksession").insert({
                "task_id": task_id,
                "user_id": user_id,
                "start_time": start_time,
                "status": "in_progress",
                "progress": 0
            }).execute()

            return JsonResponse({
                "success": True,
                "session_id": response.data[0]["session_id"]
            })

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})

@csrf_exempt
def update_progress(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            session_id = data.get("session_id")
            progress = data.get("progress")

            if not session_id:
                return JsonResponse({"success": False, "error": "Missing session_id"})

            supabase.table("tasksession").update({"progress": progress}).eq("session_id", session_id).execute()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def end_task_session(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            session_id = data.get("session_id")

            if not session_id:
                return JsonResponse({"success": False, "error": "Missing session_id"})

            supabase.table("tasksession").update({  #  lowercase name
                "end_time": timezone.localtime(timezone.now()).isoformat(),
                "status": "completed"
            }).eq("session_id", session_id).execute()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"error": "Invalid request method"}, status=400)


#  Timer page (HTML)
def task_timer(request):
    task_id = request.GET.get("task_id")
    duration = request.GET.get("duration")
    generated_task = request.GET.get("task")  # may be None

    #  Safely handle missing 'task' parameter
    if generated_task:
        generated_task = unquote(generated_task)
    else:
        generated_task = "No task description provided."

    return render(request, "task_timer.html", {
        "task_id": task_id,
        "duration": duration,
        "generated_task": generated_task
    })


#PASSWORD RESET
#  PASSWORD RESET (Using Supabase + Gmail OTP)

def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # 🔍 Check if user exists in Supabase
            check_user = supabase.table("user").select("*").eq("email", email).execute()
            print("Check user before update:", check_user.data)
            if not check_user.data:
                messages.error(request, "No account found with that email.")
                return render(request, "forgot_password.html", {"form": form})

            #  Generate and store 6-digit OTP
            otp = str(random.randint(100000, 999999))
            request.session["otp"] = otp
            request.session["email"] = email

            # Send OTP via Gmail
            try:
                send_mail(
                    subject="Your OTP Code for Password Reset",
                    message=f"Your OTP code is: {otp}\nUse this code to reset your password.",
                    from_email=os.getenv("EMAIL_HOST_USER"),  # your Gmail
                    recipient_list=[email],
                    fail_silently=False,
                )
                print(f" Sent OTP {otp} to {email}")  # Debug log
                messages.success(request, "OTP sent to your email.")
                return redirect("verify_otp")
            except Exception as e:
                print(" Email sending failed:", e)
                messages.error(request, "Failed to send email. Please try again later.")
    else:
        form = ForgotPasswordForm()

    return render(request, "forgot_password.html", {"form": form})


def verify_otp(request):
    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp_entered = form.cleaned_data['otp']
            otp_saved = request.session.get('otp')

            if otp_entered == otp_saved:
                request.session["email_verified"] = True
                messages.success(request, "OTP verified! You can now reset your password.")
                return redirect("reset_password")
            else:
                messages.error(request, "Invalid OTP. Please try again.")
    else:
        form = OTPVerificationForm()

    return render(request, "verify_otp.html", {"form": form})


def reset_password(request):
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            email = request.session.get("email")
            new_password = form.cleaned_data["new_password"]

            print("DEBUG: session email ->", email)
            print("DEBUG: new_password ->", new_password)

            if not email:
                messages.error(request, "Session expired. Please restart the password reset process.")
                return redirect("forgot_password")

            try:
                check_user = supabase.table("user").select("*").eq("email", email).execute()
                print("DEBUG: check_user response ->", check_user)
                print("DEBUG: check_user.data ->", check_user.data)

                # try update and print full response attributes
                update_response = (
                    supabase.table("user")
                    .update({"password": new_password})
                    .eq("email", email)
                    .execute()
                )

                # Print everything available on response object
                print("DEBUG: update_response ->", update_response)
                print("DEBUG: update_response.data ->", getattr(update_response, "data", None))
                print("DEBUG: update_response.status_code ->", getattr(update_response, "status_code", None))
                print("DEBUG: update_response.error ->", getattr(update_response, "error", None))

                # decide success
                if getattr(update_response, "data", None):
                    messages.success(request, "Password reset successful! You can now log in.")
                    request.session.flush()
                    return redirect("login")
                else:
                    # give a more helpful message
                    messages.error(request, " Password not updated. Check Supabase policies or server logs.")
                    print("WARN: Update returned empty data. Likely blocked by RLS/policies or permission issue.")
            except Exception as e:
                print(" Exception when resetting password:", e)
                messages.error(request, f"Something went wrong: {e}")
    else:
        form = ResetPasswordForm()

    return render(request, "reset_password.html", {"form": form})

#ADDED
def user_progress(request):
    #  Ensure user is logged in (via Supabase session)
    if "user_id" not in request.session:
        messages.warning(request, "Please log in first.")
        return redirect("login")

    user_id = request.session["user_id"]
    user_name = request.session.get("user_name", "User")

    #  Fetch this user’s tasks from Supabase
    response = supabase.table("task").select("task_type, difficulty").eq("user_id", user_id).execute()
    user_tasks = response.data or []

    #  Count totals
    total_tasks = len(user_tasks)
    stationary_counts = {"easy": 0, "medium": 0, "hard": 0}
    active_counts = {"easy": 0, "medium": 0, "hard": 0}

    for task in user_tasks:
        task_type = task.get("task_type", "").lower()
        difficulty = task.get("difficulty", "").lower()

        if task_type == "stationary" and difficulty in stationary_counts:
            stationary_counts[difficulty] += 1
        elif task_type == "active" and difficulty in active_counts:
            active_counts[difficulty] += 1

    stationary_total = sum(stationary_counts.values())
    active_total = sum(active_counts.values())

    #  Pass data to template
    context = {
        "user_name": user_name,
        "total_tasks": total_tasks,
        "stationary_total": stationary_total,
        "stationary_counts": stationary_counts,
        "active_total": active_total,
        "active_counts": active_counts,
    }

    return render(request, "user_progress.html", context)


#ADMIN
def admin_dashboard(request):
    # 🛑 Check admin access
    if not request.session.get("is_staff") and not request.session.get("is_superuser"):
        messages.error(request, "Access denied.")
        return redirect("task_dashboard")

    # --- Handle Admin Actions (POST requests) ---
    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")

        if action and user_id:
            if action == "delete":
                supabase.table("user").delete().eq("user_id", user_id).execute()
                messages.success(request, "User deleted successfully.")
            elif action == "make_admin":
                supabase.table("user").update({"is_staff": True, "is_superuser": True}).eq("user_id", user_id).execute()
                messages.success(request, "User promoted to Admin.")
            elif action == "remove_admin":
                supabase.table("user").update({"is_staff": False, "is_superuser": False}).eq("user_id", user_id).execute()
                messages.success(request, "Admin role removed.")
            return redirect("admin_dashboard")

    # --- Fetch All Users ---
    response = supabase.table("user").select("user_id, name, email, is_active, is_staff, is_superuser").execute()
    users = response.data or []

    context = {"users": users}
    return render(request, "admin_dashboard.html", context)

def profile_user(request):
    return render(request, "profile_user.html")


#Profle added
import os
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect

def profile_user(request):
    # Ensure user is logged in
    if "user_email" not in request.session:
        messages.warning(request, "Please log in first.")
        return redirect("login")

    user_name = request.session.get("user_name")
    user_email = request.session.get("user_email")

    if request.method == 'POST' and 'image' in request.FILES:
        image_file = request.FILES['image']

        # Ensure the directory exists
        save_dir = os.path.join(settings.MEDIA_ROOT, "profile_pics")
        os.makedirs(save_dir, exist_ok=True)  # ✅ creates folder if it doesn't exist

        # Sanitize filename (optional: remove spaces, etc.)
        filename = image_file.name.replace(" ", "_")

        # Full path to save
        file_path = os.path.join("profile_pics", filename)
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        # Save uploaded file
        with open(full_path, "wb+") as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # Save path in session (or database if persistent storage needed)
        request.session['profile_image'] = file_path
        return redirect('profile_user')

    # Show profile image (default if not uploaded)
    profile_image = request.session.get('profile_image', 'default_profile.png')

    context = {
        "user_name": user_name,
        "user_email": user_email,
        "profile_image": profile_image,
    }
    return render(request, "profile_user.html", context)


def admin_profile(request):
    # Ensure user is logged in
    if "user_email" not in request.session:
        messages.warning(request, "Please log in first.")
        return redirect("login")

    user_name = request.session.get("user_name")
    user_email = request.session.get("user_email")

    if request.method == 'POST' and 'image' in request.FILES:
        image_file = request.FILES['image']

        # Ensure the directory exists
        save_dir = os.path.join(settings.MEDIA_ROOT, "profile_pics")
        os.makedirs(save_dir, exist_ok=True)  # ✅ creates folder if it doesn't exist

        # Sanitize filename (optional: remove spaces, etc.)
        filename = image_file.name.replace(" ", "_")

        # Full path to save
        file_path = os.path.join("profile_pics", filename)
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        # Save uploaded file
        with open(full_path, "wb+") as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # Save path in session (or database if persistent storage needed)
        request.session['profile_image'] = file_path
        return redirect('admin_profile')

    # Show profile image (default if not uploaded)
    profile_image = request.session.get('profile_image', 'default_profile.png')

    context = {
        "user_name": user_name,
        "user_email": user_email,
        "profile_image": profile_image,
    }
    return render(request, "admin_profile.html", context)

#CHANGED
from django.shortcuts import render

def task_summary(request):
    task = request.GET.get("task", "No task description available.")
    return render(request, "task_summary.html", {"task": task})
