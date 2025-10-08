# productivity_app/urls.py
from django.urls import path
from django.shortcuts import redirect  
from . import views

urlpatterns = [
     path('', lambda request: redirect('login')), 
     
   path("register/", views.register, name="register"),
path("login/", views.login_user, name="login"),

 path("dashboard/", views.task_dashboard, name="task_dashboard"),
    path("generate-task/", views.generate_task, name="generate_task"),  # 👈 add this
]
