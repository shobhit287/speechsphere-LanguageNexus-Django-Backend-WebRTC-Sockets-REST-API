from django.contrib import admin
from django.urls import path,include
from . import views
urlpatterns = [
    path('', views.index,name="index"),
    path('signup', views.handle_signup.as_view(),name="signup_user"),
    path('login', views.handle_login.as_view(),name="login_user"),
    path('verifytoken', views.verify_token.as_view(),name="verify_token"),
    
]