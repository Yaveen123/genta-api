from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask_cors import CORS

load_dotenv()

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress a warning
db = SQLAlchemy(app)

CORS(app, resources={r"/add_user": {"origins": ["https://genta.live", "http://127.0.0.1:5000"]}})

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'



@app.route('/add_user')
def add_user():
    # new_user = User(username='new_user', email='new_user@example.com')
    # db.session.add(new_user)
    # db.session.commit()

    results = db.session.execute(db.text("SELECT * FROM user")).fetchall()
    # Process the results as needed
    data = [row._asdict() for row in results]  # Convert SQLAlchemy Row objects to dictionaries
    return jsonify(data)


@app.route('/')
def home():
    return "Hello!! This is a test env"
# Define your database models here

if __name__ == '__main__':
    # Example of creating tables (if they don't exist)
    with app.app_context():
        db.create_all()
    app.run(debug=True)