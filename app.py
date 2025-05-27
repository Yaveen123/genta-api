# Imports
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask_cors import CORS
from google.oauth2 import id_token
from google.auth.transport import requests
from functools import wraps
import uuid
from flask import redirect
from datetime import date

# Load the environment variables from the OS
load_dotenv()

# Retrieve each env var from OS as 'consts'
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')  

# Initiate flask
app = Flask(__name__)
# Connect to db using SQL alchemy
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Setup CORS (from Google API docs)
CORS(app, resources={r"/add_user": {"origins": [
    "https://genta.live",
    "http://127.0.0.1:5000",
    "http://localhost:6969"
]}})


# Setup SQL alchemy models
# SQL Alchemy (n.d.) Models and Tables https://flask-sqlalchemy.readthedocs.io/en/stable/models/
# The user table
class User(db.Model):
    #Explicitly define the table name
    __tablename__ = 'users'

    # Set the columns in the table according to data dict
    id = db.Column(db.Integer, primary_key=True)
    googleId = db.Column(db.String(21), unique=True, nullable=False)
    versionTag = db.Column(db.String(255), nullable=False) 

    # I need to define a one to many relationship here
    # cacading all using delete-orphan means that if...
    # ...a user is deleted their projects are deleted
    # ...a project is deleted their events are deleted
    # ...a event is deleted their todos are deleted
    # SQL Alchemy (2021) Linking Rels w Backref https://docs.sqlalchemy.org/en/13/orm/backref.html 
    projects = db.relationship('Project', backref='user', lazy=True, cascade="all, delete-orphan")

    # When printing the object, this function will run
    # I.e. print(thisobject) -> "<User 23908420>"
    # Tebaska, M. (2009) Purpose of __repr_ method? https://stackoverflow.com/questions/1984162/purpose-of-repr-method 
    def __repr__(self):
        return f'<User {self.googleID}>'

# Projects table
class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    userId = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Link to users table!
    projectTitle = db.Column(db.String(255), nullable=False)
    dueDate = db.Column(db.Date, nullable=False) #NOTE: date object handling?? 

    # Define relationship to events
    events = db.relationship('Event', backref='project', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Project {self.projectTitle}>'

#Events table
class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    projectId = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False) # Foreign Key to projects table
    title = db.Column(db.String(255), nullable=False)
    collapsed = db.Column(db.Boolean, nullable=False, default=False)
    dueDate = db.Column(db.Date, nullable=False) 
    notes = db.Column(db.Text) 
    todoShown = db.Column(db.Boolean, nullable=False, default=True) 
    notesShown = db.Column(db.Boolean, nullable=False, default=True)

    # Define relationship to todos
    todos = db.relationship('Todo', backref='event', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Event {self.title}>'

# Todos table
class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    eventId = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False) 
    checked = db.Column(db.Boolean, nullable=False, default=False)
    content = db.Column(db.Text) # Can be nullable

    def __repr__(self):
        return f'<Todo {self.content}>'




# Vendor provided code (Google Identity)
def verify_google_token(token):
    """Verifies the Google ID token."""
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')

        # ID token is valid and you can access user information here
        # This is vendor provided code but it isn't used; it represents what the stuff inside idinfo stores
        user_id = idinfo['sub']
        email = idinfo['email']
        # You might want to verify the 'aud' (audience) matches your client ID
        return {'user_id': user_id, 'email': email}
    except ValueError:
        # Invalid token
        return None

# Vendor provided code (Google Identity)
def token_required(f):
    """Decorator to require a valid Google ID token for accessing a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            id_token_str = auth_header.split(' ')[1]
            user_info = verify_google_token(id_token_str)
            if user_info:
                # Optionally pass the user_info to the route if needed
                return f(user_info=user_info, *args, **kwargs) # Pass the user_info var to the decorated func
            else:
                return jsonify({'message': 'Invalid Google ID token'}), 401
        else:
            return jsonify({'message': 'Authorization token is missing'}), 401
    return decorated_function


@app.route('/add_user')
@token_required
def add_user(user_info):
    # Get the user ID to retrieve the data for that user from the database
    user_id = user_info['user_id']
    return getUserDataFromDB(user_id)


def getUserDataFromDB(user_google_id):
    user_record = User.query.filter_by(googleId=user_google_id).first()
    # Like SELECT * FROM users WHERE googleID=user_google_id but SQL alchemy style 
    # and only grabs the first one (well there should only be one)
    user_db_id = None
    user_version_tag = None

    if user_record is None:
        new_version_tag = str(uuid.uuid4()) # Create a new UUID for a ver tag
        try:
            new_user = User(googleId=user_google_id, versionTag=new_version_tag) # Create a new user
            db.session.add(new_user)
            db.session.commit()
            user_db_id = new_user.id # set the variable as the actual new id now
            user_version_tag = new_version_tag
        except Exception as err:
            print(f"Error creating new user: {err}")
            db.session.rollback()
            return None
    else:
        user_db_id = user_record.id
        user_version_tag = user_record.versionTag
    
    # Failsafe if something else went wrong during creation
    # My solution is to just return a fully blank slate
    if user_db_id == None:
        return {
            "user_db_id": None,
            "user_version_tag": None,
            "projects": []
        }
    
    # Time to get every project and the data nested within them

    # Get all the projects that belong to that user
    projects_from_db = Project.query.filter_by(userId=user_db_id).all()
    assembled_projects_data = []

    # if there are any projects, for each proj get their events
    if projects_from_db:
        for current_project_from_db in projects_from_db:
            project_dict = {
                "id": current_project_from_db.id,
                "projectTitle":current_project_from_db.projectTitle,
                "dueDate":str(current_project_from_db.dueDate), # conv date to str
                "events": [],
            }

            # Get all events from db
            events_from_db = Event.query.filter_by(projectId=current_project_from_db.id)
            
            if events_from_db:
                for current_event_from_db in events_from_db:
                    event_dict = {
                        "id": current_event_from_db.id,
                        "title": current_event_from_db.title,
                        "collapsed": current_event_from_db.collapsed,
                        "dueDate": str(current_event_from_db.dueDate), # conv Date object to string
                        "notes": current_event_from_db.notes,
                        "notesShown": current_event_from_db.notesShown,
                        "todoShown": current_event_from_db.todoShown,  
                        "todo": []
                    }

                    # get the todos
                    todos_from_db = Todo.query.filter_by(eventId=current_event_from_db.id).all()
                    if todos_from_db:
                        for current_todo_from_db in todos_from_db:
                            todo_dict = {
                                "id": current_todo_from_db.id,
                                "checked": current_todo_from_db.checked,
                                "content": current_todo_from_db.content
                            }
                            event_dict["todo"].append(todo_dict)
                        project_dict["events"].append(event_dict)
                assembled_projects_data.append(project_dict)
    return {
        "user_db_id": user_db_id,
        "user_version_tag": user_version_tag,
        "projects": assembled_projects_data
    }

def editDatabase(user_db_id, projects_from_client_list, existing_projects_list_from_db):
    processed_project_ids_from_client = set() #a set stores unique IDs and all project IDs should be unique

    # Iterate through all projs to check if changes in project data
    for project_client_data in projects_from_client_list: 
        existing_project_in_db = None
        current_project_id_in_db = None

        # if theres any projects inside the client data
        if project_client_data.get('id') != None:
            
            # find a project inside existing projects where id = id in project client data
            existing_project_in_db = None
            for project in existing_projects_list_from_db:
                if project.id == project_client_data['id']:
                    existing_project_in_db = project
                    break

            # this means that genta couldnt find a project where the id in db matches the cli id
            # which should never happen (maybe a bad actor is trying to do something)
            if existing_project_in_db == None:
                return f"ERROR: Project with ID {project_client_data['id']} is not found in db for user"
            
            current_project_id_in_db = existing_project_in_db.id

            updated = False
            # If the project title has changed
            if project_client_data.get('projectTitle') != existing_project_in_db.projectTitle:
                existing_project_in_db.projectTitle = project_client_data['projectTitle']
                updated = True
            # if the duedate is within an obj or a str (could possibly be either bc idk how cli updates works atp)
            # to compare dates genta has to conv str to date obj
            # geeksforgeeks (2021) fromisoformat() function of datetime.date class in py https://www.geeksforgeeks.org/fromisoformat-function-of-datetime-date-class-in-python/ 
            # w3schools (n.d.) python isinstance() https://www.w3schools.com/python/ref_func_isinstance.asp 
            if isinstance(project_client_data.get('dueDate'), str):
                client_due_date_obj = date.fromisoformat(project_client_data['dueDate'])
            else:
                client_due_date_obj = project_client_data.get('dueDate')
            # if the client id has changed
            if client_due_date_obj != existing_project_in_db.dueDate:
                existing_project_in_db.dueDate = client_due_date_obj
                updated = True
            if updated:
                db.session.add(existing_project_in_db) # Mark for update by putting it into staging area
            
            # add the UNIQUE processed id to the set!
            processed_project_ids_from_client.add(current_project_id_in_db)

        else:
            # There isnt a project! so genta has to make a new one

            # conv date obj to str in case
            if isinstance(project_client_data.get('dueDate'), str):
                client_due_date_obj = date.fromisoformat(project_client_data['dueDate']) 
            else:
                client_due_date_obj = project_client_data.get('dueDate')

            # create a new project obj sqlalch
            new_project = Project(
                userId = user_db_id,
                projectTitle = project_client_data['projectTitle'],
                dueDate = client_due_date_obj
            )
            # add it to the db and get new id before commit for foreign keys
            db.session.add(new_project) #stage
            db.session.flush()
            current_project_id_in_db = new_project.id
            processed_project_ids_from_client.add(current_project_id_in_db) # add to list of processed ids

        # handle changing events
        # get the events
        events_from_client = project_client_data.get('events', [])
        # get from db and create a set for it
        if existing_project_in_db: 
            existing_events_in_db_for_project = existing_project_in_db.events
        else:
            existing_events_in_db_for_project = []
        processed_event_ids_for_proj = set()

        # if there are any events
        for event_client_data in events_from_client:
            existing_event_in_db = None
            current_event_in_db = None
            # if the event has an ID, make ure to check if the id a matches an event on the db
            if event_client_data.get('id') != None:
                
                existing_event_in_db = None
                for event in existing_events_in_db_for_project:
                    if event.id == event_client_data['id']:
                        existing_event_in_db = event
                        break
            
                # checks to see if there was any match
                if existing_event_in_db == None:
                    # this should never happen because the database should always have something to edit 
                    return f"ERROR: event with ID {event_client_data["id"]} is not found in table projects w id: {current_project_id_in_db}"
                
                current_event_id_in_db = existing_event_in_db.id
                updated = False

                # conv the date from str to date obj if its a str
                if isinstance(event_client_data['dueDate'], str):
                    client_event_due_date_obj = date.fromisoformat(event_client_data['dueDate'])
                else:
                    client_event_due_date_obj = event_client_data['dueDate']

                # now, genta can go through the items and check if there has been a change
                if event_client_data.get('title') != existing_event_in_db.title:
                    existing_event_in_db.title = event_client_data['title']
                    updated = True
                if event_client_data.get('collapsed') != existing_event_in_db.collapsed:
                    existing_event_in_db.collapsed = event_client_data['collapsed']
                    updated = True
                if client_event_due_date_obj != existing_event_in_db.dueDate:
                    existing_event_in_db.dueDate = client_event_due_date_obj
                    updated = True
                if event_client_data.get('notes') != existing_event_in_db.notes:
                    existing_event_in_db.notes = event_client_data['notes']
                    updated = True
                if event_client_data.get('todoShown') != existing_event_in_db.todoShown:
                    existing_event_in_db.todoShown = event_client_data['todoShown']
                    updated = True
                if event_client_data.get('notesShown') != existing_event_in_db.notesShown:
                    existing_event_in_db.notesShown = event_client_data['notesShown']
                    updated = True
                
                if updated:
                    # put the updates in session (stage) ready for db commit 
                    db.session.add(existing_event_in_db)
                
                processed_event_ids_for_proj.add(current_event_id_in_db)
            else:
                # create new event
                # conv to date obj 
                if isinstance(event_client_data['dueDate'], str):
                    client_event_due_date_obj = date.fromisoformat(event_client_data['dueDate'])
                else:
                    client_event_due_date_obj = event_client_data['dueDate']

                # create the new event in the database
                new_event = Event(
                    projectId=current_project_id_in_db,
                    title=event_client_data['title'],
                    collapsed=event_client_data['collapsed'],
                    dueDate=client_event_due_date_obj,
                    notes=event_client_data.get('notes'), # turns out i have to use .get() because the notes section can be null (stupid)
                    todoShown=event_client_data['todoShown'],
                    notesShown=event_client_data['notesShown']
                )
                # add changes to stage, get new id
                db.session.add(new_event)
                db.session.flush() 
                # get id and log 
                current_event_id_in_db = new_event.id
                processed_event_ids_for_proj.add(current_event_id_in_db)

            # time for the todos 
            # get todos from client otherwise use empty list
            todos_from_client = event_client_data.get('todo', [])
            # get the todos if they exist
            if existing_event_in_db:
                existing_todos_in_db_for_event = existing_event_in_db.todos
            else:
                existing_todos_in_db_for_event = []

            # set the id storage
            processed_todos_for_proj = set()

            # for every todo from client
            for todo_client_data in todos_from_client:
                existing_todo_in_db = None

                #  if there are actually todos
                if todo_client_data.get('id') != None:
                    # get todos that exist
                    existing_todo_in_db = None
                    for todo in existing_todos_in_db_for_event:
                        if todo.id == todo_client_data['id']:
                            existing_todo_in_db = todo
                            break
                    # otherwise raise an err (should never happen)
                    if existing_todo_in_db == None:
                        return f"ERROR: todo with id {todo_client_data["id"]} cannot be found"
                    
                    # now we can check each part of the todo item thing tos ee if its changed
                    current_todo_id_in_db = existing_todo_in_db.id
                    updated = False
                    if todo_client_data.get('checked') != existing_todo_in_db.checked:
                        existing_todo_in_db.checked = todo_client_data['checked']
                        updated = True
                    if todo_client_data.get('content') != existing_todo_in_db.content:
                        existing_todo_in_db.content = todo_client_data['content']
                        updated = True
                    # if changes are present stage them for committing
                    if updated:
                        db.session.add(existing_todo_in_db)
                    
                    processed_todos_for_proj.add(current_todo_id_in_db)
                else:
                    # create a new todo cuz it aint exist bru :(
                    # note for future readers if this sucks im way too tired this logic hurts my brain
                    new_todo = Todo(
                        eventId=current_event_id_in_db,
                        content=todo_client_data.get('content'),
                        checked=todo_client_data['checked']
                    )
                    db.session.add(new_todo)
            
            # del todos for event
            for existing_todo_item in existing_todos_in_db_for_event:
                if existing_todo_item.id not in processed_todos_for_proj:
                    db.session.delete(existing_todo_item)
        
        # del events for proj 
        for existing_event_item in existing_events_in_db_for_project:
            if existing_event_item.id not in processed_event_ids_for_proj:
                db.session.delete(existing_event_item)

    # Delete projects not in client data for user!
    for existing_project_item in existing_projects_list_from_db:
        if existing_project_item.id not in processed_project_ids_from_client:
            db.session.delete(existing_project_item)

    # try to commit all staged changes
    try:
        db.session.commit()
        return "SUCCESS"
    except Exception as err:
        db.session.rollback()
        print(f"problem w database {err}")
        return f"Database update failed: {err}"



@app.route('/')
def home():
    return "Welcome to GentaAPI"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    #app.run(debug=True)
    app.run(debug=True, host="localhost", port=6969)