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
# --- SUPABASE CONFIG ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ✅ REGISTER FUNCTION
def register(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # 1️⃣ Check if email already exists in 'user' table
        check_user = supabase.table("user").select("*").eq("email", email).execute()

        if check_user.data:
            messages.warning(request, "Account already exists. Please log in instead.")
            return redirect("login")

        # 2️⃣ Insert new user
        data = {
            "name": name,
            "email": email,
            "password": password,  # ⚠️ For testing; use hash later
        }

        response = supabase.table("user").insert(data).execute()

        print("📦 Supabase Insert Response:", response)

        if response.data:
            messages.success(request, "Registration successful! You can now log in.")
            return redirect("login")
        else:
            messages.error(request, "Something went wrong while saving your account.")
            return render(request, "register.html")

    return render(request, "register.html")


# ✅ LOGIN FUNCTION
def login_user(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # 3️⃣ Check credentials in 'user' table
        response = supabase.table("user").select("*").eq("email", email).eq("password", password).execute()

        print("🔍 Login Query Response:", response)

        if response.data:
            """
            messages.success(request, f"Welcome back, {response.data[0]['name']}!")
            #CHANGED
            return render(request, "task_dashboard.html")
            """
            # ✅ CHANGED Save user session
            request.session["user_email"] = response.data[0]["email"]
            request.session["user_name"] = response.data[0]["name"]
            request.session["user_id"] = response.data[0]["user_id"]  # <-- Add this

            messages.success(request, f"Welcome back, {response.data[0]['name']}!")
            return redirect("task_dashboard")  # redirect to the dashboard page
        
        else:
            messages.error(request, "Account does not exist or invalid credentials.")
            return render(request, "login.html")

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

            # 🧠 AI prompt
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

            # 🔑 Load OpenRouter API key securely
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
              print("⚠️ OpenRouter error:", ai_result)
              return JsonResponse({
                 "success": False,
                 "error": ai_result.get("error", ai_result)
             })


            # ✅ Extract generated text
            generated_task = ai_result["choices"][0]["message"]["content"].strip()

            # ✅ Extract generated text
            generated_task = ai_result["choices"][0]["message"]["content"].strip()

            # 💾 Save to Supabase "task" table
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
            print("❌ Error generating task:", e)
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

        # 🧠 Example: generate a simple task description (you can replace this with your AI call later)
        generated_task = f"A {difficulty} {task_type} task for {duration} minutes ({frequency} frequency)."

        # ✅ Redirect to the result page, passing the generated task as a query parameter
        return redirect(f'/result/?task={generated_task}')

    # if not POST, just show the duration selection page
    return render(request, "task_duration.html")

def task_result(request):
    task_param = request.GET.get("task", "")
    generated_task = unquote(task_param)
    return render(request, "task_result.html", {"generated_task": generated_task})