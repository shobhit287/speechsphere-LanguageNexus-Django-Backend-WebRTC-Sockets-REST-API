from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from rest_framework.views import APIView
from datetime import datetime, timedelta, timezone
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password,check_password
import pymongo
import jwt
import uuid
from django.conf import settings
# Create your views here.
def index(request):
    return HttpResponse("<h1>Server is Running</h1>")

class handle_signup(APIView):
    def post(self,request):
      try:
        data=request.data
        client=pymongo.MongoClient(settings.DATABASE_URL)
        db=client.languagePlatform
        users_collection=db.users
        hashed_password=make_password(data['signup_password'])
        check_user_existence=users_collection.find_one({"Email":data['signup_email']})
        if check_user_existence is None:
         user={"ID":str(uuid.uuid4()),"First Name":data['signup_firstname'],"Last Name":data ['signup_lastname'],"Email":data['signup_email'],"Password":hashed_password,"Gender":data ['signup_gender'],"Nationality":data['signup_nationality']}
         insert_user=users_collection.insert_one(user)
         client.close()
         return JsonResponse({"status":True},status=201)
        else:
         return JsonResponse({"status":False, "message": "User with this email already exists"}, status=409)
      except:
           return JsonResponse({"status":False},status=400)

def generate_jwt(ID):
   expiration_time = datetime.now(timezone.utc) + timedelta(days=10)
   payload = {'userid': ID,'expiration_time':expiration_time.isoformat()}
   jwt_token = jwt.encode(payload,key=settings.JWT_KEY ,algorithm='HS256')
   return jwt_token
    
class handle_login(APIView):
   def post(self,request):
    try:
      data=request.data
      client=pymongo.MongoClient(settings.DATABASE_URL)
      db=client.languagePlatform
      users_collection=db.users
      check_user=users_collection.find_one({"Email":data['login_email']})
      if check_user:
         if check_password(data['login_password'],check_user['Password']):
            token=generate_jwt(check_user['ID'])
            return JsonResponse({"token":token,"status":True},status=200) 
         else:
            return JsonResponse({"Message":"Invalid Credentials","status":False},status=401)   
      else:
         return JsonResponse({"Message":"Invalid Credentials","status":False},status=401)  
    except:
       return JsonResponse({"Message":"Error While Authenicating the User","status":False},status=400) 
   
def verify_token_function(token):
   try:
     payload=jwt.decode(token,key=settings.JWT_KEY ,algorithms='HS256')
     expiration_time = datetime.fromisoformat(payload['expiration_time'])
     if datetime.now(timezone.utc) > expiration_time:
        return False,None
     return True,payload
   except:
      return False,None

class verify_token(APIView):
   def post(self,request):
      token=request.headers.get('Authorization')
      token_status,payload=verify_token_function(token)
      if token_status:
       return JsonResponse({"status": token_status},status=200)
      else:
         return JsonResponse({"status": False},status=401)
      

class queryForm(APIView):
   def post(self,request):
      data=request.data   
      try:
            send_mail(
                f"QUERY FROM {data['contactus_email']}",
                f"Name: {data['contactus_name']}\nEmail: {data['contactus_email']}\nMessage: {data['contactus_description']}",
                data['contactus_email'],  
                [settings.EMAIL_HOST_USER],  
                fail_silently=False,
            )   
            return JsonResponse({"status": True}, status=200)
      except Exception as e:
            print("ERROR:", e)
            return JsonResponse({"status": False}, status=500)


