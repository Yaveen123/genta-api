from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask_cors import CORS
from google.oauth2 import id_token
from google.auth.transport import requests
from functools import wraps

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')  # Ensure you have this in your .env file

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app, resources={r"/add_user": {"origins": ["https://genta.live", "http://127.0.0.1:5000", "http://localhost:6969"]}})

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

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

    results = db.session.execute(db.text("SELECT * FROM user")).fetchall()
    data = [row._asdict() for row in results]
    return jsonify(data)

@app.route('/')
def home():
    return "Hello!! This is a test env"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)