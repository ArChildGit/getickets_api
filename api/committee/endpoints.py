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
committee_endpoints = Blueprint('committee', __name__)

@committee_endpoints.route('/add/<int:event_id>', methods=['POST'])
@jwt_required()
def add_committee(event_id):
    """Endpoint to add a committee member to an event (only accessible by admin and event owner)."""
    try:
        # Get data from JWT for user verification
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles()  # Get roles from JWT

        # Ensure the user is an admin
        if 'admin' not in user_roles:
            return jsonify({"message": "You must be an admin to add committee members."}), 403

        # Verify the current user is the owner of the event
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM events WHERE id = %s", (event_id,))
                result = cursor.fetchone()

                if not result or result[0] != user_id:
                    return jsonify({"message": "You are not authorized to manage this event."}), 403

        # Get parameters from the request
        id_user = request.form.get('id_user')

        if not id_user:
            return jsonify({"message": "'id_user' is required."}), 400

        # Add the committee member
        with get_connection() as connection:
            with connection.cursor() as cursor:
                insert_query = """
                    INSERT INTO panitia (id_user, id_acara)
                    VALUES (%s, %s)
                """
                cursor.execute(insert_query, (id_user, event_id))
                connection.commit()

                if cursor.rowcount > 0:
                    return jsonify({"message": "Committee member added successfully."}), 201
                else:
                    return jsonify({"message": "Failed to add committee member."}), 500

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@committee_endpoints.route('/list/<int:event_id>', methods=['GET'])
def get_committees(event_id):
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                query = """
                    SELECT p.id, p.id_user, u.username
                    FROM panitia p
                    JOIN user u ON p.id_user = u.id
                    WHERE p.id_acara = %s
                """
                cursor.execute(query, (event_id,))
                results = cursor.fetchall()

                committees = [
                    {"id": row[0], "id_user": row[1], "username": row[2]} for row in results
                ]

        return jsonify({"committees": committees}), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@committee_endpoints.route('/my-committee', methods=['GET'])
@jwt_required()
def get_user_committees():
    try:
        # Dapatkan user_id dari JWT
        current_user = get_jwt_identity()
        user_id = current_user['id']

        with get_connection() as connection:
            with connection.cursor() as cursor:
                query = """
                    SELECT e.id, e.gambar, e.nama, e.deskripsi, e.tanggal, 
                           e.lokasi, e.user_id, u.username AS event_manager
                    FROM panitia p
                    JOIN events e ON p.id_acara = e.id
                    JOIN user u ON e.user_id = u.id
                    WHERE p.id_user = %s
                """
                cursor.execute(query, (user_id,))
                results = cursor.fetchall()

                events = [
                    {
                        "id": row[0],
                        "image": row[1],
                        "name": row[2],
                        "description": row[3],
                        "date": row[4],
                        "location": row[5],
                        "user_id": row[6],
                        "event_manager": row[7]
                    }
                    for row in results
                ]

        return jsonify({"events": events}), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@committee_endpoints.route('/delete/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_committee(event_id):
    """Endpoint to delete a committee member by their ID (only accessible by the user themselves or an admin who is also the event owner)."""
    try:
        # Get data from JWT for user verification
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles()  # Get roles from JWT

        # Get committee_id from request
        committee_id = request.form.get('id_user')

        # Ambil ID pemilik acara dari database
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM events WHERE id = %s", (event_id,))
                result = cursor.fetchone()
                event_owner_id = result[0] if result else None

        # Cek apakah pengguna berhak menghapus:
        if str(user_id) == committee_id:  # Orang terkait sendiri
            allow_delete = True
        elif 'admin' in user_roles and user_id == event_owner_id:  # Admin yang juga pemilik acara
            allow_delete = True
        else:
            allow_delete = False

        if not allow_delete:
            return jsonify({"message": "You are not authorized to delete this committee member."}), 403

        # Hapus panitia
        with get_connection() as connection:
            with connection.cursor() as cursor:
                delete_query = "DELETE FROM panitia WHERE id_user = %s AND id_acara = %s"
                cursor.execute(delete_query, (committee_id, event_id))
                connection.commit()

                if cursor.rowcount > 0:
                    return jsonify({"message": "Committee member deleted successfully."}), 200
                else:
                    return jsonify({"message": "Committee member not found or deletion failed."}), 404

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@committee_endpoints.route('/quit/<int:event_id>', methods=['DELETE'])
@jwt_required()
def quit_committee(event_id):
    """Endpoint for a committee member to quit an event by removing themselves."""
    try:
        # Get user ID from JWT
        current_user = get_jwt_identity()
        user_id = current_user['id']

        # Remove the user from the committee
        with get_connection() as connection:
            with connection.cursor() as cursor:
                delete_query = "DELETE FROM panitia WHERE id_user = %s AND id_acara = %s"
                cursor.execute(delete_query, (user_id, event_id))
                connection.commit()

                if cursor.rowcount > 0:
                    return jsonify({"message": "You have successfully quit the committee."}), 200
                else:
                    return jsonify({"message": "You are not part of this committee or already removed."}), 404

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500