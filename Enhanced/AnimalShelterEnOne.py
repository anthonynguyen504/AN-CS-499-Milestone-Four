from pymongo import MongoClient, ASCENDING
from bson.json_util import dumps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import DuplicateKeyError

# Initialize Flask app with static and template directories
app = Flask(__name__, static_folder='static', template_folder='pages')
app.secret_key = 'supersecretkey'  # Used for session management and CSRF protection

class AnimalShelter(object):
    """ CRUD operations for Animal collection in MongoDB """

    def __init__(self):
        try:
            # Establish a connection to MongoDB
            self.client = MongoClient('mongodb://localhost:27017')
            self.database = self.client['AAC']  # AAC is the database name
            print("DEBUG: Connected to MongoDB successfully.")

            # Create unique indexes to ensure no duplicate records
            self.database.animals.create_index([('animal_id', ASCENDING)], unique=True)
            self.database.animals.create_index([('name', ASCENDING)])
            self.database.animals.create_index([('breed', ASCENDING)])
            print("DEBUG: Indexes created on animal_id, name, and breed.")
        except Exception as e:
            print(f"ERROR: Could not connect to MongoDB. {e}")

    # Method to create a new animal record in the collection
    def create(self, data):
        if data:
            try:
                # Insert data into the animals collection
                result = self.database.animals.insert_one(data)
                if result.inserted_id:
                    print(f"DEBUG: Data added with ID: {result.inserted_id}")
                    return result.inserted_id  # Return the inserted document ID
            except Exception as e:
                print(f"ERROR: Failed to insert document. {e}")
                raise Exception("ERROR: Failed to insert document")
        else:
            raise ValueError("ERROR: Nothing to save, the data parameter is empty")

    # Method to read animal records from the collection
    def read(self, data=None):
        try:
            if data:
                print(f"DEBUG: Searching for records with parameters: {data}")
                result = self.database.animals.find(data)  # Find matching records
            else:
                print("DEBUG: No search parameters provided. Retrieving all records.")
                result = self.database.animals.find()  # Retrieve all records

            result_list = list(result)  # Convert cursor to list
            if result_list:
                print(f"DEBUG: Found {len(result_list)} record(s).")
                return result_list
            else:
                print("DEBUG: No results found, returning empty list.")
                return []  # Return an empty list if no results are found
        except Exception as e:
            print(f"ERROR: Failed to retrieve data. Exception: {e}")
            raise Exception(f"ERROR: Failed to retrieve data: {e}")

    # Method to update an existing record
    def update(self, data, new_data):
        if not data:
            raise ValueError("ERROR: No search parameter specified for update")
        if not new_data:
            raise ValueError("ERROR: No update parameter specified")

        try:
            print(f"DEBUG: Updating record(s) with search parameter: {data}")
            # Update record and return the modified document
            result = self.database.animals.find_one_and_update(data, {"$set": new_data}, return_document=True)
            if result:
                print(f"DEBUG: Record updated: {dumps(result)}")
                return result
            else:
                raise Exception("ERROR: Update failed, search parameter not found")
        except Exception as e:
            print(f"ERROR: Failed to update record(s). {e}")
            raise Exception("ERROR: Failed to update record(s)")

    # Method to delete a record based on search parameters
    def delete(self, data):
        if not data:
            raise ValueError("ERROR: No search parameter specified for deletion")

        try:
            print(f"DEBUG: Deleting record(s) with parameter: {data}")
            # Delete the record and check if it was deleted
            result = self.database.animals.delete_one(data)
            if result.deleted_count > 0:
                print(f"DEBUG: Delete successful. Deleted {result.deleted_count} record(s).")
                return result.deleted_count  # Return the number of records deleted
            else:
                raise Exception("ERROR: No records matched the deletion criteria")
        except Exception as e:
            print(f"ERROR: Failed to delete record(s). {e}")
            raise Exception("ERROR: Failed to delete record(s)")

    # Method to run aggregation pipelines for complex queries
    def aggregate(self, pipeline):
        """ Run aggregation pipelines to perform complex queries """
        try:
            print(f"DEBUG: Running aggregation pipeline: {pipeline}")
            result = self.database.animals.aggregate(pipeline)
            return list(result)  # Return the aggregation result as a list
        except Exception as e:
            print(f"ERROR: Failed to run aggregation pipeline. {e}")
            raise Exception("ERROR: Failed to run aggregation pipeline")

# User Handling for registration and login
class UserHandler:
    """User handling operations for registering and logging in."""
    def __init__(self):
        try:
            # Establish a MongoDB connection for user handling
            self.client = MongoClient('mongodb://localhost:27017')
            self.database = self.client['AAC']
            self.database.users.create_index([('username', ASCENDING)], unique=True)
            print("DEBUG: Connected to MongoDB successfully for User Handling.")
        except Exception as e:
            print(f"ERROR: Could not connect to MongoDB for user handling. {e}")

    # Register a new user with a hashed password
    def register_user(self, username, password, role):
        """Register a new user with hashed password."""
        try:
            hashed_password = generate_password_hash(password)  # Hash the password
            user_data = {
                'username': username,
                'password': hashed_password,
                'role': role
            }
            # Insert the user data into the users collection
            self.database.users.insert_one(user_data)
            print(f"DEBUG: User {username} registered successfully.")
        except DuplicateKeyError:
            raise Exception("ERROR: Username already exists. Choose a different username.")
        except Exception as e:
            print(f"ERROR: Failed to register user. {e}")
            raise Exception(f"ERROR: Failed to register user: {e}")

    # Verify if the user exists and the password matches
    def verify_user(self, username, password):
        """Verify if the user exists and the password matches."""
        user = self.database.users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            return user  # Return user data if the password is correct
        return None

# Initialize AnimalShelter and UserHandler classes
animal_shelter = AnimalShelter()
user_handler = UserHandler()

# API Routes

@app.route('/')
def home():
    """Home page that lists all animals with update and delete buttons."""
    try:
        animals = animal_shelter.read()  # Call the read method to fetch all animals
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
        # Get username and password from the form
        username = request.form['username']
        password = request.form['password']
        user = user_handler.verify_user(username, password)

        if user:
            session['username'] = username  # Set session variables
            session['role'] = user['role']
            return redirect(url_for('home'))
        else:
            return "Invalid credentials", 401  # Return error if authentication fails

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for registering a new user."""
    if request.method == 'POST':
        # Get registration details from the form
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
    session.pop('username', None)  # Clear session variables
    session.pop('role', None)
    return redirect(url_for('login'))

@app.before_request
def check_permissions():
    """Check user permissions before accessing certain routes."""
    if 'username' not in session and request.endpoint not in ['login', 'register', 'home']:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    if session.get('role') != 'admin' and request.endpoint in ['create_animal', 'update_animal', 'delete_animal']:
        return "Access denied. Only admins can perform this action.", 403  # Check for admin role

@app.route('/create', methods=['GET', 'POST'])
def create_animal():
    """API endpoint to create a new animal record."""
    if request.method == 'POST':
        data = request.form.to_dict()
