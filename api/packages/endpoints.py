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
from helper.checker import validate_price

from helper.db_helper import get_connection

bcrypt = Bcrypt()
packages_endpoints = Blueprint('packages', __name__)

@packages_endpoints.route('/get/<int:id_acara>', methods=['GET'])
def get_packages_by_event(id_acara):
    """Endpoint to get all packages related to a specific event."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Query to get packages related to the given event ID
                query = """
                    SELECT 
                        p.id, 
                        p.id_acara, 
                        p.name, 
                        p.tickets_per_package, 
                        p.total_tickets_available, 
                        p.price
                    FROM packages p
                    WHERE p.id_acara = %s
                """
                cursor.execute(query, (id_acara,))
                results = cursor.fetchall()

                packages_list = []
                for row in results:
                    packages_list.append({
                        "id": row[0],
                        "id_acara": row[1],
                        "name": row[2],
                        "tickets_per_package": row[3],
                        "total_tickets_available": row[4],
                        "price": float(row[5])
                    })

        return jsonify({
            "event_id": id_acara,
            "packages": packages_list
        }), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@packages_endpoints.route('/add/<int:id_acara>', methods=['POST'])
@jwt_required()
def create_package(id_acara):
    """Endpoint untuk membuat paket baru."""
    try:
        # Ambil data dari JWT untuk verifikasi pengguna
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles()  # Ambil roles pengguna dari JWT

        # Verifikasi apakah pengguna adalah admin atau pemilik event
        if 'admin' not in user_roles:
            return jsonify({"message": "You do not have permission to create a package for this event."}), 403

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM events WHERE id = %s", (id_acara,))
                event_owner = cursor.fetchone()

                if not event_owner or event_owner[0] != user_id:
                    return jsonify({"message": "You do not have permission to create a package for this event."}), 403

        # Ambil data dari form
        name = request.form.get('name')
        tickets_per_package = request.form.get('tickets_per_package')
        total_tickets_available = request.form.get('total_tickets_available')
        price = request.form.get('price')

        # Validasi input
        if not all([name, tickets_per_package, total_tickets_available, price]):
            return jsonify({"message": "All fields are required."}), 400

        valid_price = validate_price(price)
        if valid_price is None:
            return jsonify({"message": "Invalid price. Price must be an integer."}), 400

        with get_connection() as connection:
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO packages (id_acara, name, tickets_per_package, total_tickets_available, price)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (id_acara, name, tickets_per_package, total_tickets_available, valid_price))
                connection.commit()
                
                # Dapatkan ID dari record yang baru dimasukkan
                cursor.execute("SELECT LAST_INSERT_ID()")
                new_id = cursor.fetchone()[0]

        return jsonify({"message": "Package created successfully.", "id": new_id}), 201
    
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@packages_endpoints.route('/delete/<int:id_acara>/<int:package_id>', methods=['DELETE'])
@jwt_required()
def delete_package(id_acara, package_id):
    """Endpoint to delete a package by its ID within an event."""
    try:
        # Ambil data dari JWT untuk verifikasi pengguna
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles()  # Ambil roles pengguna dari JWT

        # Verifikasi apakah pengguna adalah admin
        if 'admin' not in user_roles:
            return jsonify({"message": "You do not have permission to delete this package."}), 403

        # Verifikasi apakah pengguna adalah pemilik event
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM events WHERE id = %s", (id_acara,))
                event_owner = cursor.fetchone()

                # Cek apakah pengguna adalah pemilik event
                if not event_owner or event_owner[0] != user_id:
                    return jsonify({"message": "You do not have permission to delete this package."}), 403

                # Cek apakah package ada di event yang sesuai
                cursor.execute("SELECT id FROM packages WHERE id = %s AND id_acara = %s", (package_id, id_acara))
                package = cursor.fetchone()

                if not package:
                    return jsonify({"message": "Package not found for this event."}), 404

                # Hapus package
                cursor.execute("DELETE FROM packages WHERE id = %s", (package_id,))
                connection.commit()

        return jsonify({"message": "Package deleted successfully."}), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@packages_endpoints.route('/packages/<int:package_id>', methods=['POST'])
def update_package(package_id):
    """Endpoint to update a package (partial updates allowed)."""
    try:
        name = request.form.get('name')
        tickets_per_package = request.form.get('tickets_per_package')
        total_tickets_available = request.form.get('total_tickets_available')
        price = request.form.get('price')

        if not any([name, tickets_per_package, total_tickets_available, price]):
            return jsonify({"message": "No fields provided for update."}), 400

        fields_to_update = []
        values_to_update = []

        if name:
            fields_to_update.append("name=%s")
            values_to_update.append(name)
        if tickets_per_package:
            fields_to_update.append("tickets_per_package=%s")
            values_to_update.append(int(tickets_per_package))
        if total_tickets_available:
            fields_to_update.append("total_tickets_available=%s")
            values_to_update.append(int(total_tickets_available))
        if price:
            fields_to_update.append("price=%s")
            values_to_update.append(float(price))

        if fields_to_update:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    update_query = f"""
                        UPDATE packages
                        SET {', '.join(fields_to_update)}
                        WHERE id=%s
                    """
                    values_to_update.append(package_id)
                    cursor.execute(update_query, values_to_update)
                    connection.commit()

                    if cursor.rowcount > 0:
                        return jsonify({"message": "Package updated successfully.", "id": package_id}), 200
                    else:
                        return jsonify({"message": "Package not found or update failed."}), 404

        return jsonify({"message": "No valid fields provided for update."}), 400

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500
