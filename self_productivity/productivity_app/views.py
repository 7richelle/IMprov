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
#
# --- SUPABASE CONFIG ---
load_dotenv()

SUPABASE_URL = "https://urwfbvpkohuiscyefknw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVyd2ZidnBrb2h1aXNjeWVma253Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkwMzU2NTYsImV4cCI6MjA3NDYxMTY1Nn0.LkKC17vpGOCElyAb8GKntVvOLX1Xygq5-kWkoY5MdNk"

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
                f"Generate one {task_type} productivity task that is {difficulty} difficulty, "
                f"should last about {duration}, and is meant to be done {frequency}. "
                f"Make it sound short, motivating, and specific."
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
                    "model": "deepseek/deepseek-chat-v3.1:free",
                    "messages": [
                        {"role": "system", "content": "You are a helpful productivity coach."},
                        {"role": "user", "content": prompt},
                    ],
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


