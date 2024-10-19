#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from pymongo import MongoClient, ASCENDING
from bson.json_util import dumps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import DuplicateKeyError

app = Flask(__name__, static_folder='static', template_folder='pages')
app.secret_key = 'supersecretkey'  # Used for session management

class AnimalShelter(object):
    """ CRUD operations for Animal collection in MongoDB """

    def __init__(self):
        try:
            self.client = MongoClient('mongodb://localhost:27017')
            self.database = self.client['AAC']
            print("DEBUG: Connected to MongoDB successfully.")
            self.database.animals.create_index([('animal_id', ASCENDING)], unique=True)
            self.database.animals.create_index([('name', ASCENDING)])
            self.database.animals.create_index([('breed', ASCENDING)])
            print("DEBUG: Indexes created on animal_id, name, and breed.")
        except Exception as e:
            print(f"ERROR: Could not connect to MongoDB. {e}")

    def create(self, data):
        if data:
            try:
                result = self.database.animals.insert_one(data)
                if result.inserted_id:
                    print(f"DEBUG: Data added with ID: {result.inserted_id}")
                    return result.inserted_id
            except Exception as e:
                print(f"ERROR: Failed to insert document. {e}")
                raise Exception("ERROR: Failed to insert document")
        else:
            raise ValueError("ERROR: Nothing to save, the data parameter is empty")

    def read(self, data=None):
        try:
            if data:
                print(f"DEBUG: Searching for records with parameters: {data}")
                result = self.database.animals.find(data)
            else:
                print("DEBUG: No search parameters provided. Retrieving all records.")
                result = self.database.animals.find()

            result_list = list(result)
            if result_list:
                print(f"DEBUG: Found {len(result_list)} record(s).")
                return result_list
            else:
                print("DEBUG: No results found, returning empty list.")
                return []  # Return an empty list if no animals are found
        except Exception as e:
            print(f"ERROR: Failed to retrieve data. Exception: {e}")
            raise Exception(f"ERROR: Failed to retrieve data: {e}")

    def update(self, data, new_data):
        if not data:
            raise ValueError("ERROR: No search parameter specified for update")
        if not new_data:
            raise ValueError("ERROR: No update parameter specified")

        try:
            print(f"DEBUG: Updating record(s) with search parameter: {data}")
            result = self.database.animals.find_one_and_update(data, {"$set": new_data}, return_document=True)
            if result:
                print(f"DEBUG: Record updated: {dumps(result)}")
                return result
            else:
                raise Exception("ERROR: Update failed, search parameter not found")
        except Exception as e:
            print(f"ERROR: Failed to update record(s). {e}")
            raise Exception("ERROR: Failed to update record(s)")

    def delete(self, data):
        if not data:
            raise ValueError("ERROR: No search parameter specified for deletion")

        try:
            print(f"DEBUG: Deleting record(s) with parameter: {data}")
            result = self.database.animals.delete_one(data)
            if result.deleted_count > 0:
                print(f"DEBUG: Delete successful. Deleted {result.deleted_count} record(s).")
                return result.deleted_count
            else:
                raise Exception("ERROR: No records matched the deletion criteria")
        except Exception as e:
            print(f"ERROR: Failed to delete record(s). {e}")
            raise Exception("ERROR: Failed to delete record(s)")

    def aggregate(self, pipeline):
        """ Run aggregation pipelines to perform complex queries """
        try:
            print(f"DEBUG: Running aggregation pipeline: {pipeline}")
            result = self.database.animals.aggregate(pipeline)
            return list(result)
        except Exception as e:
            print(f"ERROR: Failed to run aggregation pipeline. {e}")
            raise Exception("ERROR: Failed to run aggregation pipeline")

# User Handling for registration and login
class UserHandler:
    """User handling operations for registering and logging in."""
    def __init__(self):
        try:
            self.client = MongoClient('mongodb://localhost:27017')
            self.database = self.client['AAC']
            self.database.users.create_index([('username', ASCENDING)], unique=True)
            print("DEBUG: Connected to MongoDB successfully for User Handling.")
        except Exception as e:
            print(f"ERROR: Could not connect to MongoDB for user handling. {e}")

    def register_user(self, username, password, role):
        """Register a new user with hashed password."""
        try:
            hashed_password = generate_password_hash(password)
            user_data = {
                'username': username,
                'password': hashed_password,
                'role': role
            }
            self.database.users.insert_one(user_data)
            print(f"DEBUG: User {username} registered successfully.")
        except DuplicateKeyError:
            raise Exception("ERROR: Username already exists. Choose a different username.")
        except Exception as e:
            print(f"ERROR: Failed to register user. {e}")
            raise Exception(f"ERROR: Failed to register user: {e}")

    def verify_user(self, username, password):
        """Verify if the user exists and the password matches."""
        user = self.database.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            return user
        return None

# Initialize AnimalShelter and UserHandler classes
animal_shelter = AnimalShelter()
user_handler = UserHandler()

# API Routes

@app.route('/')
def home():
    """Home page that lists all animals with update and delete buttons."""
    try:
        animals = animal_shelter.read()  # Call the read method
        if not animals:  # If no animals are found
            no_animals = True
        else:
            no_animals = False
        return render_template('home.html', animals=animals, no_animals=no_animals)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route for authentication"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = user_handler.verify_user(username, password)

        if user:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('home'))
        else:
            return "Invalid credentials", 401

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for registering a new user."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # admin or staff

        try:
            user_handler.register_user(username, password, role)
            return redirect(url_for('login'))  # Redirect to login after successful registration
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logout the current user"""
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.before_request
def check_permissions():
    """Check user permissions before accessing certain routes."""
    if 'username' not in session and request.endpoint not in ['login', 'register', 'home']:
        return redirect(url_for('login'))
    
    if session.get('role') != 'admin' and request.endpoint in ['create_animal', 'update_animal', 'delete_animal']:
        return "Access denied. Only admins can perform this action.", 403

@app.route('/create', methods=['GET', 'POST'])
def create_animal():
    """API endpoint to create a new animal record."""
    if request.method == 'POST':
        data = request.form.to_dict()
        try:
            result = animal_shelter.create(data)
            return redirect(url_for('home'))
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    return render_template('create.html')

@app.route('/update/<animal_id>', methods=['GET'])
def update_animal_form(animal_id):
    """Render the update form for the given animal_id with pre-filled data."""
    try:
        # Fetch the animal data by its ID
        animal = animal_shelter.read({"animal_id": animal_id})
        if not animal:
            return "Animal not found", 404
        return render_template('update.html', animal=animal[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/update', methods=['POST'])
def update_animal():
    """API endpoint to update an animal record."""
    animal_id = request.form.get('animal_id')  # Get the animal_id from the form
    if not animal_id:
        return "Error: Missing animal ID.", 400

    new_data = request.form.to_dict()  # Get new data from the form
    try:
        result = animal_shelter.update({"animal_id": animal_id}, new_data)
        return redirect(url_for('home'))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/delete', methods=['POST'])
def delete_animal():
    """API endpoint to delete an animal record."""
    data = request.get_json()  # Get the JSON data from the request
    animal_id = data.get('animal_id')  # Extract the animal_id from the JSON payload

    print(f"DEBUG: Received animal_id: {animal_id}")  # Debug print

    if not animal_id:
        return jsonify({"error": "Missing animal ID."}), 400

    try:
        result = animal_shelter.delete({"animal_id": animal_id})
        return jsonify({"success": True}), 200  # Send a success response
    except Exception as e:
        return jsonify({"error": str(e)}), 400  # Return error as JSON response



@app.route('/reports', methods=['GET'])
def generate_report():
    """API endpoint to generate a report of animals by breed"""
    try:
        pipeline = [
            {"$group": {"_id": "$breed", "total": {"$sum": 1}}},
            {"$sort": {"total": -1}}
        ]
        report = animal_shelter.aggregate(pipeline)
        return render_template('report.html', report=report)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Running the Flask server
if __name__ == '__main__':
    try:
        app.run(debug=True, use_reloader=False, port=5001)
    except Exception as e:
        print(f"ERROR: Failed to start the Flask server. {e}")


# In[ ]:





# In[ ]:




