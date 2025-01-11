from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, decode_token
from flask_bcrypt import Bcrypt
import os
import uuid
from datetime import timedelta
from werkzeug.utils import secure_filename
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from helper.jwt_helper import get_roles

from helper.db_helper import get_connection

bcrypt = Bcrypt()
user_endpoints = Blueprint('user', __name__)
UPLOAD_FOLDER = "img/profile"

#Fetch User Data
@user_endpoints.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Endpoint to get the user's profile data based on the ID from the token."""
    try:
        current_user = get_jwt_identity()
        user_id = current_user['id']  # Ambil ID pengguna dari token

        # Retrieve user data from the database
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, email, nama, nomor_telepon, foto_user, roles 
                    FROM user 
                    WHERE id=%s
                """, (user_id,))
                result = cursor.fetchone()

                if result:
                    # Format response as a dictionary
                    user_data = {
                        "id": result[0],
                        "username": result[1],
                        "email": result[2],
                        "nama": result[3],
                        "nomor_telepon": result[4],
                        "foto_user": result[5],  # Bisa diubah jika ingin mengirimkan URL lengkap
                        "roles": result[6]
                    }
                    return jsonify({"user": user_data}), 200
                else:
                    return jsonify({"message": "User not found."}), 404

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@user_endpoints.route('/ticket-owner/<int:ticket_id>', methods=['GET'])
def get_ticket_owner(ticket_id):
    """Endpoint untuk mendapatkan data pemilik tiket berdasarkan ticket_id dari URI path."""
    try:
        if not ticket_id:
            return jsonify({"success": False, "message": "Ticket ID diperlukan."}), 400

        # Ambil data pengguna berdasarkan tickets.id
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        u.id, u.username, u.nama, u.nomor_telepon, u.foto_user
                    FROM tickets t
                    JOIN user u ON t.user_id = u.id
                    WHERE t.id = %s
                """, (ticket_id,))
                
                result = cursor.fetchone()

                if result:
                    user_data = {
                        "id": result[0],
                        "username": result[1],
                        "name": result[2],
                        "phone": result[3],
                        "photo": result[4],  # Pastikan ini adalah URL jika gambar tersimpan sebagai path
                    }
                    return jsonify({"success": True, "data": user_data}), 200
                else:
                    return jsonify({"success": False, "message": "Tiket tidak ditemukan atau tidak memiliki pemilik."}), 404

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"success": False, "message": "Terjadi kesalahan.", "error": str(e)}), 500

#Update User Data
@user_endpoints.route('/update', methods=['POST'])
@jwt_required()
def update():
    """Endpoint to update a user's profile."""
    try:
        current_user = get_jwt_identity()
        user_id = current_user['id']

        # Extract fields from form
        nama = request.form.get('nama')
        nomor_telepon = request.form.get('nomor_telepon')
        password = request.form.get('password')
        foto_user = request.files.get('foto_user')

        if not any([nama, nomor_telepon, password, foto_user]):
            return jsonify({"message": "No fields provided for update."}), 400

        fields_to_update = []
        values_to_update = []

        if nama:
            fields_to_update.append("nama=%s")
            values_to_update.append(nama)
        if nomor_telepon:
            fields_to_update.append("nomor_telepon=%s")
            values_to_update.append(nomor_telepon)
        if password:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            fields_to_update.append("password=%s")
            values_to_update.append(hashed_password)

        if foto_user and foto_user.filename != '':
            try:
                # Retrieve current profile picture from database
                with get_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT foto_user FROM user WHERE id=%s", (user_id,))
                        result = cursor.fetchone()
                        current_profile_picture = result[0] if result else None

                # Generate a new filename using user_id, a unique identifier, and preserve the original extension
                unique_id = uuid.uuid4().hex  # Generate a unique identifier
                file_extension = os.path.splitext(foto_user.filename)[1]
                new_filename = f"{user_id}_{unique_id}{file_extension}"
                file_path = os.path.join(UPLOAD_FOLDER, new_filename)

                # Ensure the directory exists
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                # Log the file path for debugging
                current_app.logger.debug(f"Saving new profile picture to {file_path}")

                # Delete the old profile picture if it exists
                if current_profile_picture:
                    old_file_path = os.path.join(UPLOAD_FOLDER, current_profile_picture)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        current_app.logger.debug(f"Deleted old profile picture at {old_file_path}")

                # Save the new profile picture
                foto_user.save(file_path)
                current_app.logger.debug(f"Saved new profile picture successfully.")

                fields_to_update.append("foto_user=%s")
                values_to_update.append(new_filename)
            except Exception as e:
                current_app.logger.error(f"Error handling profile picture upload: {e}")
                return jsonify({"message": "Error handling profile picture upload.", "error": str(e)}), 500

        if fields_to_update:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    update_query = f"UPDATE user SET {', '.join(fields_to_update)} WHERE id=%s"
                    values_to_update.append(user_id)

                    cursor.execute(update_query, values_to_update)
                    connection.commit()
                    rows_affected = cursor.rowcount

                    if rows_affected > 0:
                        return jsonify({"user_id": user_id, "message": "Profile updated successfully."}), 200
                    else:
                        return jsonify({"message": "User not found or profile update failed."}), 404

        return jsonify({"message": "No valid fields provided for update."}), 400

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

# Delete user
@user_endpoints.route('/delete/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Endpoint to delete a user based on user ID. Only accessible by an admin."""
    try:
        # Get roles using the helper function
        roles = get_roles()

        # Tambahkan log untuk debugging
        current_app.logger.debug(f"Roles from token: {roles}")

        # Periksa jika salah satu peran adalah 'admin'
        if 'admin' not in roles:
            return jsonify({"message": "Access denied. Only admins can delete users."}), 403

        # Perform deletion
        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Check if the user exists before attempting to delete
                cursor.execute("SELECT id FROM user WHERE id=%s", (user_id,))
                result = cursor.fetchone()
                if not result:
                    return jsonify({"message": "User not found."}), 404

                # Delete the user
                cursor.execute("DELETE FROM user WHERE id=%s", (user_id,))
                connection.commit()
                rows_affected = cursor.rowcount

                if rows_affected > 0:
                    return jsonify({"message": f"User with ID {user_id} deleted successfully."}), 200
                else:
                    return jsonify({"message": "Failed to delete the user."}), 500

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500
