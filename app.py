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
                return f(*args, **kwargs)
            else:
                return jsonify({'message': 'Invalid Google ID token'}), 401
        else:
            return jsonify({'message': 'Authorization token is missing'}), 401
    return decorated_function


@app.route('/add_user')
@token_required
def add_user():
    # The user is authenticated at this point
    # You can now access user information if you modified the decorator
    # For example, if you passed user_info:
    # user_email = user_info['email']
    # Check if the user exists in your database or create a new one

    # results = db.session.execute(db.text("SELECT * FROM todos")).fetchall()
    # data = [row._asdict() for row in results]
    # return jsonify(data)

    return getUserDataFromDB("123456789")








@app.route('/')
def home():
    return "Welcome to Genta API"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    #app.run(debug=True)
    app.run(debug=True, host="localhost", port=6969)