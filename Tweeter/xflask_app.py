
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, request, redirect, render_template, session, make_response
from flask_session import Session
from datetime import datetime

import random

import json

import boto3
import uuid


app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

AWSKEY = ''
AWSSECRET =''
PUBLIC_BUCKET = ''
STORAGE_URL = ''

def get_public_bucket():
    s3 = boto3.resource(service_name='s3', region_name='us-east-2', aws_access_key_id=AWSKEY, aws_secret_access_key=AWSSECRET)
    bucket = s3.Bucket(PUBLIC_BUCKET)
    return bucket

#helper function to get a dynamobd table
def get_table(name):
    client = boto3.resource(service_name='dynamodb', region_name='us-east-2', aws_access_key_id=AWSKEY, aws_secret_access_key=AWSSECRET)
    table = client.Table(name)
    return table



def add_remember_key(email):
    table = get_table("Remember")
    key = str(uuid.uuid4()) + str(uuid.uuid4()) + str(uuid.uuid4())

    item = {"key":key, "email":email}
    table.put_item(Item=item)
    return key

#brings you to the homepage and adds the current user to the profile link in the dropdown menu
@app.route('/')
def home_page_final():
    if is_logged_in():
        username = session['username']
        return render_template('xhometemp.html', username=username);
    return redirect('/static/xlogin.html')
    #return redirect('/static/xhome.html')

#creates a new profile with a blank photo link in the table
@app.route('/create_profile', methods=['POST'])
def create_profile():
    table = get_table('xusers')
    uid = str(uuid.uuid4())
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    upload = {'uid':uid, 'username':username, 'email':email, 'password':password, 'photo':''}

    table.put_item(Item=upload)

    return {'result':'OK', 'username':username, 'uid':uid}


#list all posts
@app.route('/listposts')
def listposts():
    table = get_table('xposts')
    posts = []
    for item in table.scan()['Items']:
        parent_pid = item['parent_pid']
        if parent_pid != '':
            continue

        date = item['date']
        text = item['text']
        pid = item['pid']
        uid = item['uid']
        user = get_user_by_uid(uid)
        username = user["username"]
        post = {'date':date, 'text':text, 'username':username, 'uid':uid, 'pid':pid}
        posts.append(post)

    posts_sorted = sorted(posts, key=lambda x: x['date'], reverse=True)

    return {'posts':posts_sorted}

#list only the posts from the user you are looking at
@app.route('/list_users_posts')
def listusersposts():
    table = get_table('xposts')
    posts = []
    user_uid = request.args.get('uid')

    for item in table.scan()['Items']:
        if item['uid'] == user_uid:
            date = item['date']
            text = item['text']
            pid = item['pid']
            uid = item['uid']
            user = get_user_by_uid(uid)
            username = user["username"]
            post = {'date':date, 'text':text, 'username':username, 'uid':uid, 'pid':pid}
            posts.append(post)

    posts_sorted = sorted(posts, key=lambda x: x['date'], reverse=True)

    return {'posts':posts_sorted}

#lists the replies of a post
@app.route('/list_replies')
def listreplies():
     table = get_table('xposts')
     results = []
     parent_pid = request.args.get('parent_pid')
     #list the replies
     for Item in table.scan()['Items']:
         if Item["parent_pid"] != parent_pid:
             continue

         uid = Item['uid']
         date = Item['date']
         text = Item['text']
         user = get_user_by_uid(uid)
         username = user["username"]

         upload = {'date':date, 'text':text, 'username':username}
         results.append(upload)
         results_sorted = sorted(results, key=lambda x: x['date'], reverse=True)


     return {'results':results_sorted}






#create a new post
@app.route('/post', methods=['POST'])
def post():
    uid = session["uid"]
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pid = str(uuid.uuid4())


    table = get_table('xposts')
    text = request.form.get('text')
    upload = {'uid':uid, 'text':text, 'date':today, 'pid': pid, 'parent_pid': ''}
    table.put_item(Item=upload)

    return {'results':'OK'}

#reply to a post
@app.route('/post_reply', methods=['POST'])
def post_reply():
    uid = session["uid"]
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pid = str(uuid.uuid4())


    table = get_table('xposts')
    text = request.form.get('text')
    parent_pid = request.form.get('parent_pid')
    upload = {'uid':uid, 'text':text, 'date':today, 'pid': pid, 'parent_pid': parent_pid}
    table.put_item(Item=upload)

    return {'results':'OK'}


def get_user_by_uid(uid):
    table = get_table('xusers')
    result = table.get_item(Key={"uid":uid})
    if 'Item' not in result:
        return None
    return result['Item']


#opens replies of a post
@app.route('/replies/<pid>')
def post_view(pid):
     table = get_table('xposts')
     item = table.get_item(Key={"pid":pid})
     item = item['Item']

     user = get_user_by_uid(item['uid'])

     return render_template('replies.html', text=item['text'], username=user['username'], date=item['date'], pid=pid)


def get_user_by_email(email):
    table = get_table('xusers')
    for item in table.scan()['Items']:
        if item['email'] == email:
            return item
    return None

def get_user_by_username(username):
    table = get_table('xusers')
    for item in table.scan()['Items']:
        if item['username'] == username:
            return item
    return None



@app.route('/login')
def login():
    email = request.args.get("email")
    password = request.args.get("password")

    #table = get_table("xusers")
    Item = get_user_by_email(email)
    #Item = table.get_item(Key={"email":email})

    if Item == None:
        return {'result': 'Email not found'}
    user = Item

    if password != user['password']:
        return {'result':'Password does not match.'}

    session["email"] = user["email"]
    session["username"] = user["username"]
    session["uid"] = user["uid"]

    result = {'result':'OK'}

    response = make_response(result)

    remember = request.args.get("remember")
    if (remember == "no"):
        response.set_cookie("remember", "")
    else:
        key = add_remember_key(user["email"])
        response.set_cookie("remember", key, max_age=60*60*24*14) #remember for 14 days

    return response

def is_logged_in():
    if not session.get("email"):
        return auto_login()
    return True

def auto_login():
    cookie = request.cookies.get("remember")
    if cookie is None:
        return False

    table = get_table("Remember")
    result = table.get_item(Key = {"key":cookie})
    if 'Item' not in result:
        return False

    remember = result['Item'] #row in the remember me table

    table = get_table("Users")
    result = table.get_item(Key={"email":remember["email"]})

    user = result['Item'] #row from the users table

    session["email"] = user["email"]
    session["username"] = user["username"]

    return True


@app.route('/logout')
def logout():
    session.pop("email", None)
    session.pop("username", None)
    session.pop("uid", None)

    response = make_response(redirect('/'))
    response.delete_cookie("remember")
    return response



#opens a profile page for a user
#need to add a way to upload a new profile photo but only if you are looking at your own profile
@app.route('/profile/<username>')
def profile(username):
    user = get_user_by_username(username)
    uid = user['uid']
    photo = user['photo']
    # if not is_logged_in() or session['username'] != username:
    #     return redirect('/')
    # Load user data based on username, if necessary
    if username == session["username"]:
        return render_template('xuserprofile.html', username=username, uid=uid, photo=photo)  # Render the profile page with profile picture upload

    return render_template('xotherprofile.html', username=username, uid=uid, photo=photo) #render the profile page without profile pictuer upload



@app.route('/uploadfile', methods=['POST'])
def uploadfile():
    bucket = get_public_bucket()
    file = request.files["file"]
    filename = file.filename



    ct = "image/jpeg"
    if filename.endswith(".png"):
        ct = "image/png"


    bucket.upload_fileobj(file, filename, ExtraArgs={"ContentType":ct})

    bucketlink = "https://ctway-web-public.s3.us-east-2.amazonaws.com/"
    full_filename = bucketlink + filename

    uid = str(uuid.uuid4())
    # filename = uid + "-" + filename;

    table = get_table('xusers')

    uid = session['uid']
    table.update_item(Key={'uid': uid},
    UpdateExpression='set photo=:photo',
    ExpressionAttributeValues={':photo': full_filename}
    )




    return {'results':'OK'}







