from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.conf import settings
from .views import verify_token_function
from motor.motor_asyncio import AsyncIOMotorClient

users_list=[]

async def userHandle(token):
    client=AsyncIOMotorClient(settings.DATABASE_URL)
    db=client.languagePlatform
    users_collection=db.users
    status,payload=verify_token_function(token)
    if payload:
      user=await users_collection.find_one({"ID":payload['userid']})
      return user
    return False

class handleVideoChat(AsyncWebsocketConsumer):
    global users_list
    async def connect(self):
        self.token = self.scope['url_route']['kwargs']['token']
        await self.accept()
        user_details=await userHandle(self.token)
        if user_details:
                not_user_existence=True
                for user in list(users_list):
                    for key,value in user.items():
                        if key=='id' and value==user_details['ID']:
                           not_user_existence=False
                if not_user_existence:
                    await self.channel_layer.group_add(settings.GROUP_NAME,self.channel_name)
                    await self.add_user(user_details)
                    await self.channel_layer.group_send(settings.GROUP_NAME,{
                        'type':'send_all_users',
                        'all_users':users_list
                    })
                else:
                    await self.close()

        


    async def send_all_users(self,event):
        modified_users=[]
        for user in event['all_users']:
            for key,value in user.items():
                if key=="channel_name" and value != self.channel_name:
                    modified_data={'id':user['id'],
                                'name':user['name'],
                                'status':user['status'],
                                'gender':user['gender']
                                }
                    modified_users.append(modified_data)
                    break       
        final_msg={'type':'users_info','data':modified_users}
        await self.send(json.dumps(final_msg))          


    async def add_user(self,user_details):
        user_to_store={
            'id':user_details['ID'],
            'name':user_details['First Name'],
            'status':False,
            'channel_name':self.channel_name,
            'gender':user_details['Gender']
        }
        users_list.append(user_to_store)



    async def receive(self, text_data=None,bytes_data=None):
        data=json.loads(text_data)
        print(data)
        if(data['type']=="create_offer"):
          remote_user_channel_name=None
          offered_user_name=None
          offered_user_id=None
          for user in list(users_list):
              for key,value in user.items():
                  if key=="id" and value==data['remote_id']:
                      remote_user_channel_name=user['channel_name']
                  if key=="channel_name" and value==self.channel_name:
                      offered_user_name=user['name']
                      offered_user_id=user['id']
                      break
                  
          await self.channel_layer.group_send(settings.GROUP_NAME,{
              'type':'send_offer_to_remote',
              'remote_channel_name':remote_user_channel_name,
              'remote_user_name':offered_user_name,
              'offer':data['offer_sdp'],
              'remote_id':offered_user_id
          })

        if(data['type']=="create_ice_candidates"):
          remote_user_channel_name=None
          for user in list(users_list):
              for key,value in user.items():
                  if key=="id" and value==data['remote_id']:
                      remote_user_channel_name=user['channel_name']
                      break
                 
                  
          await self.channel_layer.group_send(settings.GROUP_NAME,{
              'type':'send_ice_candidates',
              'remote_channel_name':remote_user_channel_name,
              'candidate':data['candidates'],
          })

        if(data['type']=="answer_ice_candidates"):
          remote_user_channel_name=None
          for user in list(users_list):
              for key,value in user.items():
                  if key=="id" and value==data['remote_id']:
                      remote_user_channel_name=user['channel_name']
                      break
                 
                  
          await self.channel_layer.group_send(settings.GROUP_NAME,{
              'type':'answer_ice_candidates',
              'remote_channel_name':remote_user_channel_name,
              'candidate':data['candidates'],
          })

        if data['type']=='rejected':
            remote_user_channel_name=None
            remote_user_name=None
            for user in list(users_list):
                for key,value in user.items():
                    if key=='id' and value==data['user_id']:
                        remote_user_channel_name=user['channel_name']
                    if key=='channel_name' and value==self.channel_name:    
                        remote_user_name=user['name']
                        break
    
            if remote_user_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'call_rejected_handle',
                    'remote_channel_name':remote_user_channel_name,
                    'remote_user_name':remote_user_name
                })

        if data['type']=="cancelled_by_offered_user":
            remote_channel_name=None
           
            for user in list(users_list):
                for key,value in user.items():
                    print(key,value)
                    if key=="id" and value==data['remote_user_id']:
                        remote_channel_name=user['channel_name']
            
          
            if remote_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'cancelled_by_offered_user',
                    'remote_channel_name':remote_channel_name
                })            

        if data['type']=='answer_offer':
            remote_channel_name=None
            for user in list(users_list):
                for key, value in user.items():
                    if key=='id' and value==data['remote_id']:
                        remote_channel_name=user['channel_name']

            if remote_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'answer_offer',
                    'remote_channel_name':remote_channel_name,
                    'answer_offer_sdp':data['offer_sdp']
                })

        if data['type']=='call_connected_success':
            remote_channel_name=None
            for user in list(users_list):
                for key,value in user.items():
                    if key=="id" and value==data['remote_id']:
                        remote_channel_name=user['channel_name']
                        user['status']=True
                    if key=="channel_name" and value==self.channel_name:
                        user['status']=True

            if remote_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'call_connected_success',
                    'remote_channel_name':remote_channel_name
                }) 
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                        'type':'send_all_users',
                        'all_users':users_list
                    })
            
        if data['type']=="call_disconnected_by_user":
            remote_channel_name=None
            for user in list(users_list):
                for key,value in user.items():
                    if key=='id' and value==data['remote_id']:
                        remote_channel_name=user['channel_name']
                        user['status']=False

                    if key=="channel_name" and value==self.channel_name:
                        user['status']=False
                        break

            if remote_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'call_disconnected_by_user',
                    'remote_channel_name':remote_channel_name
                })  

                await self.channel_layer.group_send(settings.GROUP_NAME,{
                        'type':'send_all_users',
                        'all_users':users_list
                    })      

        if data['type']=='user_leave':
            remote_channel_name=None
            try:
                for user in list(users_list):  
                    for key,value in user.items():
                        if key=="id" and value==data['remote_id']:
                            remote_channel_name=user['channel_name']
                            user['status']=False
            except :
                print("Error")                

            if remote_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'user_leave',
                    'remote_channel_name':remote_channel_name

                })  

            await self.channel_layer.group_send(settings.GROUP_NAME,{
                        'type':'send_all_users',
                        'all_users':users_list
                    })    

        if data['type']=="text_message":
            remote_channel_name=None
            for user in list(users_list):   
                for key,value in user.items():
                    if key=='id' and value==data['remote_id']:
                        remote_channel_name=user['channel_name']
                        break
            if remote_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'send_text_msg',
                    'remote_channel_name':remote_channel_name,
                    'msg':data['msg']

                })    

        if data['type']=="candidates_create":
            remote_channel_name=None
            for user in list(users_list):   
                for key,value in user.items():
                    if key=='id' and value==data['remote_id']:
                        remote_channel_name=user['channel_name']
                        break

            if remote_channel_name:
                await self.channel_layer.group_send(settings.GROUP_NAME,{
                    'type':'candidates_create',
                    'remote_channel_name':remote_channel_name,
                    'candidates':data['candidates']

                })    

       

    async def candidates_create(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'candidates_create','candidates':event['candidates']}
            await self.send(json.dumps(data))   

    async def send_text_msg(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'recieved_msg','msg':event['msg']}
            await self.send(json.dumps(data))              
                                                 

    async def user_leave(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'user_leave'}
            await self.send(json.dumps(data))

    async def call_disconnected_by_user(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'call_disconnected_by_user'}
            await self.send(json.dumps(data))

    async def call_connected_success(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'call_connected_success'}
            await self.send(json.dumps(data))

    async def answer_offer(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'call_accepted','answer_sdp':event['answer_offer_sdp']}
            await self.send(json.dumps(data))

    async def cancelled_by_offered_user(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'cancelled_by_offered_user'}
            await self.send(json.dumps(data))


    async def call_rejected_handle(self,event):
        if self.channel_name==event['remote_channel_name']:
            data={'type':'rejected','rejected_by':event['remote_user_name']}
            await self.send(json.dumps(data))





    async def send_offer_to_remote(self,event):
        if self.channel_name==event['remote_channel_name']:
            data_to_send={'type':'recieved_offer','offered_by':event['remote_user_name'],'offer':event['offer'],'offered_user_id':event['remote_id']}  
            await self.send(json.dumps(data_to_send))  

    async def send_ice_candidates(self,event):
        if self.channel_name==event['remote_channel_name']:
            data_to_send={'type':'create_ice_candidates','candidate':event['candidate']}  
            await self.send(json.dumps(data_to_send))  

    async def answer_ice_candidates(self,event):
        if self.channel_name==event['remote_channel_name']:
            data_to_send={'type':'answer_ice_candidates','candidate':event['candidate']}  
            await self.send(json.dumps(data_to_send))  

    async def disconnect(self, code):
       await self.channel_layer.group_discard(settings.GROUP_NAME,self.channel_name)
       for user in list(users_list):
           for key,value in user.items():
               if key=="channel_name" and value==self.channel_name:
                   users_list.remove(user)
                   break
       
       await self.channel_layer.group_send(settings.GROUP_NAME,{
          'type':'send_user_after_disconnect',
       })         

    async def send_user_after_disconnect(self,event):
         modified_users=[]
         for user in list(users_list):
            for key,value in user.items():
                if key=="channel_name" and value!=self.channel_name:
                    modified_data={'id':user['id'],
                                        'name':user['name'],
                                        'status':user['status'],
                                        'gender':user['gender']
                                        }
                    modified_users.append(modified_data)
                    break
         final_msg={'type':'users_info','data':modified_users}   
         await self.send(json.dumps(final_msg))
