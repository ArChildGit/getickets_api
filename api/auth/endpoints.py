from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, decode_token
from flask_bcrypt import Bcrypt
import os
import uuid
from datetime import timedelta
from werkzeug.utils import secure_filename
from helper.checker import validate_password_strength

from helper.db_helper import get_connection

bcrypt = Bcrypt()
auth_endpoints = Blueprint('auth', __name__)

@auth_endpoints.route('/login', methods=['POST'])
def login():
    """Route for user authentication and token generation"""
    username = request.form.get('username')
    password = request.form.get('password')

    # Ensure both username and password are provided
    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    # Connect to the database and fetch the user by username
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM User WHERE username = %s", (username,))
        user = cursor.fetchone()

        # If user does not exist or the password is incorrect
        if not user or not bcrypt.check_password_hash(user['password'], password):
            return jsonify({"msg": "Bad username or password"}), 401

        # Generate an access token using the user's ID as the identity
        access_token = create_access_token(
            identity={'id': user['id']},  # Use ID instead of username
            additional_claims={'roles': user['roles']},  # Include roles in additional claims
            expires_delta=timedelta(hours=2)
        )

        # Decode the token to extract expiration time
        decoded_token = decode_token(access_token)
        expires = decoded_token['exp']

        return jsonify({
            "access_token": access_token,
            "expires_in": expires,
            "type": "Bearer"
        })
    
    except Exception as e:
        return jsonify({
            "message": "Failed",
            "description": str(e)
        }), 500
    
    finally:
        cursor.close()  # Always close the cursor
        connection.close()  # Always close the connection

@auth_endpoints.route('/register', methods=['POST'])
def register():
    """Route for user registration"""
    nama = request.form.get('nama')
    nomor_telepon = request.form.get('nomor_telepon')
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    file = request.files.get('foto_user')  # Get the file if provided

    # Ensure required fields are present
    if not nama or not nomor_telepon or not email or not username or not password:
        return jsonify({"msg": "All fields are required"}), 400

    # Validasi kekuatan password
    password_strength = validate_password_strength(password)
    if password_strength == "Weak":
        return jsonify({"msg": "Password is too weak. Use at least 6 characters."}), 400

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Default to None for file path
    foto_user_path = None
    
    # Save the file if provided
    if file:
        unique_filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        full_path = os.path.join(current_app.root_path, 'img', 'profile', unique_filename)
        file.save(full_path)
        foto_user_path = unique_filename  # Store only the filename in DB

    # Connect to the database and insert the user
    connection = get_connection()
    cursor = connection.cursor()

    try:
        insert_query = """
        INSERT INTO User (nama, nomor_telepon, email, username, password, foto_user)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (nama, nomor_telepon, email, username, hashed_password, foto_user_path))
        connection.commit()

        new_id = cursor.lastrowid

        if new_id:
            return jsonify({
                "message": "OK",
                "description": "User created successfully",
                "username": username
            }), 201
        else:
            return jsonify({
                "message": "Failed",
                "description": "Unable to create user"
            }), 500

    except Exception as e:
        connection.rollback()
        return jsonify({
            "message": "Failed",
            "description": str(e)
        }), 500

    finally:
        cursor.close()  # Always close the cursor
        connection.close()  # Always close the connection

# BOOKS LATIHAN
# @auth_endpoints.route('/login', methods=['POST'])
# def login():
#     """Routes for authentication"""
#     username = request.form['username']
#     password = request.form['password']

#     if not username or not password:
#         return jsonify({"msg": "Username and password are required"}), 400

#     connection = get_connection()
#     cursor = connection.cursor(dictionary=True)
#     query = "SELECT * FROM users WHERE username = %s AND deleted_at IS NULL"
#     request_query = (username,)
#     cursor.execute(query, request_query)
#     user = cursor.fetchone()
#     cursor.close()

#     if not user or not bcrypt.check_password_hash(user.get('password'), password):
#         return jsonify({"msg": "Bad username or password"}), 401

#     access_token = create_access_token(
#         identity={'username': username}, additional_claims={'roles': "add_your_roles"})
#     decoded_token = decode_token(access_token)
#     expires = decoded_token['exp']
#     return jsonify({"access_token": access_token, "expires_in": expires, "type": "Bearer"})


# @auth_endpoints.route('/register', methods=['POST'])
# def register():
#     """Routes for register"""
#     username = request.form['username']
#     password = request.form['password']
#     # To hash a password
#     hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

#     connection = get_connection()
#     cursor = connection.cursor()
#     insert_query = "INSERT INTO users (username, password) values (%s, %s)"
#     request_insert = (username, hashed_password)
#     cursor.execute(insert_query, request_insert)
#     connection.commit()
#     cursor.close()
#     new_id = cursor.lastrowid
#     if new_id:
#         return jsonify({"message": "OK",
#                         "description": "User created",
#                         "username": username}), 201
#     return jsonify({"message": "Failed, cant register user"}), 501
