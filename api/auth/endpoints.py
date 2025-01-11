"""Routes for module books"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, decode_token
from flask_bcrypt import Bcrypt

from helper.db_helper import get_connection

bcrypt = Bcrypt()
auth_endpoints = Blueprint('auth', __name__)


@auth_endpoints.route('/login', methods=['POST'])
def login():
    """Routes for authentication"""
    username = request.form['username']
    password = request.form['password']

    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    query = "SELECT * FROM users WHERE username = %s AND deleted_at IS NULL"
    request_query = (username,)
    cursor.execute(query, request_query)
    user = cursor.fetchone()
    cursor.close()

    if not user or not bcrypt.check_password_hash(user.get('password'), password):
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(
        identity={'username': username}, additional_claims={'roles': "add_your_roles"})
    decoded_token = decode_token(access_token)
    expires = decoded_token['exp']
    return jsonify({"access_token": access_token, "expires_in": expires, "type": "Bearer"})


@auth_endpoints.route('/register', methods=['POST'])
def register():
    """Routes for register"""
    nama = request.form['nama']
    nomor_telepon = request.form['nomor_telepon']
    email = request.form['email']
    username = request.form['username']
    password = request.form['password']
    foto_user = request.form.get('foto_user')  # Get photo if available, else None

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    connection = get_connection()
    cursor = connection.cursor()
    
    # Insert query
    insert_query = """
    INSERT INTO User (nama, nomor_telepon, email, username, password, foto_user)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    request_insert = (nama, nomor_telepon, email, username, hashed_password, foto_user)
    
    try:
        cursor.execute(insert_query, request_insert)
        connection.commit()
        new_id = cursor.lastrowid
        cursor.close()
        
        if new_id:
            return jsonify({"message": "OK", "description": "User created", "username": username}), 201
    except Exception as e:
        connection.rollback()
        cursor.close()
        return jsonify({"message": "Failed", "description": str(e)}), 501

