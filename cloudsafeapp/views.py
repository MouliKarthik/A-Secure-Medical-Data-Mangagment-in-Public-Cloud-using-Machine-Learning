from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
import django.contrib.messages as messages
from django.core.exceptions import ValidationError
import pandas as pd
import numpy as np
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from cloudsafeapp.mechanism import get_it_encrypted, get_it_decrypted
from azure.cosmos import CosmosClient,exceptions,PartitionKey
from bson import ObjectId
import datetime
import json
import uuid

# ---- Home and Error


client = CosmosClient(URL,credential=KEY)

DATABASE_NAME = 'TodoList'
CONTAINER_NAME= "ITEMS"

def home_view(request):
    return render(request, "home.html")


def custom_404_view(request, exception):
    print("[EXCEPTION] ", exception)
    return render(request, "404.html", status=404)


# ---- AUTHENTICATION AND AUTHORIZATION


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        print(form)
        if form.is_valid():
            username = form.cleaned_data["username"]
            print(username)
            try:
                create_initial_collection(username)
            except Exception as e:
                messages.error(
                    request, f"Could not create a collection named {username}"
                )
                print("[EXCEPTION] ", e)
                return render(request, "register.html")
            user = form.save()
            login(request, user)
            messages.success(
                request, f"Welcome {username}! You have successfully registered."
            )
            return redirect("dashboard")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request, f"Welcome {user.username}! You have successfully logged in."
            )
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    messages_to_display = messages.get_messages(request)
    return render(
        request, "login.html", {"form": form, "messages": messages_to_display}
    )


def logout_view(request):
    logout(request)
    messages.success(request, "Successfully logged out.")
    return redirect("login")  # Redirect to login page after logout


# ---- DASHBOARD


@login_required
def dashboard_view(request):
    messages_to_display = messages.get_messages(request)
    return render(request, "dashboard.html", {"messages": messages_to_display})


# ---- FUNCTIONS


@login_required
def upload_view(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        password = request.POST.get("password")
        try:
            handle_file_upload_encrypt(request, uploaded_file, password)
            #handle_file_upload(request, uploaded_file, password)
            messages.success(request, "Successfully uploaded data.")
            return redirect("dashboard")
        except (ValidationError, ConnectionFailure, KeyError) as e:
            messages.error(request, "Internal Error Occured.")
            print("[EXCEPTION] ", e)
            return render(
                request, "upload.html"
            )  # Render the upload page with the error message
    else:
        return render(request, "upload.html")


@login_required
def fetch_view(request):
    if request.method == "GET":
        username = request.user.username
        collection = get_collection(username)
        #user_uploads_cursor = collection.find({}, {"filename": 1, "upload_date": 1})
        user_uploads=collection.query_items(f'select * from container con where con.username="{username}"',enable_cross_partition_query=True)
        # for upload in user_uploads:
        #     upload["id_str"] = str(upload["id"])
        uploads_data = []  # Prepare data for rendering
        for upload in user_uploads:
            # Extract necessary information from the upload
            upload_data = {
                "filename": upload.get("filename"),
                "upload_date": upload.get("upload_date"),
                "id_str": str(upload.get("id"))
            }
            uploads_data.append(upload_data) 
        
        context = {"user_uploads": uploads_data}
        
        return render(request, "fetch.html", context)
    else:
        return redirect("dashboard")  # Redirect to dashboard for non-GET requests

@login_required
def fetch_file_view(request, file_id):
    password = password = request.POST.get("password")
    context = {"file_id": file_id}
    if password:
        username = request.user.username
        collection = get_collection(username)
        #file_data = collection.find_one({"_id": ObjectId(file_id)})
        file_data=collection.query_items(f'select * from container con where con.id="{file_id}"',enable_cross_partition_query=True)
        #print(file_data)
        encrypted_data = []  # Prepare encrypted data for decryption
        for item in file_data:
            encrypted_data=item.get("data", {})
        #print(encrypted_data)
        if encrypted_data:
            try:
                decrypted_data = get_it_decrypted(encrypted_data, password)
                if decrypted_data:
                    context["decrypted_data"] = decrypted_data
                    messages.success(request, "Successfully decrypted data.")
                else:
                    messages.error(request, "Decrypted Data is not returned.")
            except ValueError as e:
                messages.error(request, "Wrong password. Please try again.")
                print("[EXCEPTION] ", e)
        else:
            messages.error(request, "File not found.")
    messages_to_display = messages.get_messages(request)
    context["messages"] = messages_to_display
    return render(request, "fetch_file.html", context=context)


# ---- DATABASE


# helper to upload file (just for testing)
def handle_file_upload(request, file, password):
    username = request.user.username
    print(username)
    collection = get_collection(username)
    df = pd.read_csv(file)
    
    # Drop rows with any missing values (NaNs)
    df.dropna(inplace=True)
    
    # Replace non-finite values (NaN, inf) with a default value (e.g., -1)
    default_value = -1
    float_columns = df.select_dtypes(include=['float']).columns
    df[float_columns] = df[float_columns].replace([np.nan, np.inf, -np.inf], default_value)
    
    # Convert float columns to integer dtype
    for col in df.columns:
        if df[col].dtype == float:
            df[col] = df[col].astype(str)
    
    # Convert DataFrame to dictionary
    data_dict = df.to_dict(orient="records")
    
    # Add additional information to data_dict
    upload_date = datetime.datetime.now().isoformat()
    
    data_dict = {
        "id": str(uuid.uuid4()),
        "username": username,
        "filename": file.name,
        "upload_date": upload_date,
        "data": data_dict
    }
    print(type(data_dict))
    # Convert data_dict to JSON
    json_data = json.dumps(data_dict)
    print(type(json_data))
    #collection.create_item(body={'id':'1','S.No': 32, 'NAME': 'JOTHIMANI M', 'YEAR': 'III CSE', 'BLOOD': 'B-', 'AGE': 19, 'CONTACT No.': 8883908536, 'LAST DONATED': '24.01.2018'})
    collection.upsert_item(body=data_dict)
    #collection.insert_one(data_upload)


# helper to upload file
def handle_file_upload_encrypt(request, file, password):
    username = request.user.username
    collection = get_collection(username)
    #print(collection)
    df = pd.read_csv(file)
    newdf, sensitivity = get_it_encrypted(df, password)
    upload_date = datetime.datetime.now().isoformat()
    data_upload = {
        "id": str(uuid.uuid4()),
        "username": username,
        "filename": file.name,
        "upload_date": upload_date,
        "data": newdf.to_dict(orient="records"),
        "sensitivity": sensitivity,
    }
    print(data_upload)
    # Serialize the data payload to JSON
    json_data_upload = json.dumps(data_upload)
    
    # Load the JSON data back into a dictionary
    data_dict = json.loads(json_data_upload)
    
    # Create an item in CosmosDB
    collection.create_item(body=data_dict)
    #collection.insert_one(data_upload)


def create_initial_collection(collection_name):
    try:
        collection = get_collection(collection_name)
        df = {
            "msg": "This is a sample data uploaded at the time of your registration. Collection init successful"
        }
        upload_date = datetime.datetime.now().isoformat()
        data_upload = {
            "id": str(uuid.uuid4()),
            "username": "infinull",
            "filename": "initial-sample",
            "upload_date": upload_date,
            "data": df,
        }
        print(data_upload)
        collection.create_item(body=data_upload)
    except (ConnectionFailure, KeyError) as e:
        raise Exception(f"Failed to create initial collection: {str(e)}")


def get_collection(collection_name):
    try:
        #client = MongoClient("mongodb+srv://smoulikarthik:UdImqhIk9PqPOi3b@cluster0.rek4yhp.mongodb.net/")
        # client = MongoClient("mongodb+srv://smoulikarthik:Akshaya.123@mongo-cosmos-host-proof.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000")
        # client.admin.command("ismaster")  # Check if connection is successful
        # db = client["cloudsafe-db"]
        database = client.create_database(DATABASE_NAME)
        print('Database created')
        container = database.create_container(id=CONTAINER_NAME,partition_key=PartitionKey(path='/id',kind='Hash'))
        print('Created')
        return container
        #return db[collection_name]
    except exceptions.CosmosResourceExistsError:
        database = client.get_database_client(DATABASE_NAME)
        container = database.get_container_client(CONTAINER_NAME)
        print('already exists')
        return container
    except KeyError:
        raise KeyError(f"Database '{collection_name}' not found.")
