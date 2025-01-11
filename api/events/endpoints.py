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
events_endpoints = Blueprint('events', __name__)
UPLOAD_FOLDER = "img/events"

@events_endpoints.route('/events', methods=['GET'])
def get_all_events():
    """Endpoint to get paginated events data with user info"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search_query = request.args.get('search', '').strip()
        offset = (page - 1) * per_page

        # Debugging: Print nilai parameter
        print(f"Request parameters - page: {page}, per_page: {per_page}, search_query: '{search_query}', offset: {offset}")

        with get_connection() as connection:
            with connection.cursor() as cursor:
                base_query = """
                    SELECT events.id, events.gambar, events.nama, events.deskripsi, events.tanggal, events.lokasi, events.user_id, user.username
                    FROM events
                    LEFT JOIN user ON events.user_id = user.id
                """
                count_query = "SELECT COUNT(*) FROM events"
                where_clause = ""
                params = []

                if search_query:
                    where_clause = "WHERE events.nama LIKE %s OR events.deskripsi LIKE %s"
                    params = [f"%{search_query}%", f"%{search_query}%"]
                    # Debugging: Print query dan parameters pencarian
                    print(f"Search query: '{search_query}' -> WHERE clause: {where_clause} with params {params}")

                # Debugging: Print query count
                print(f"Executing count query: {count_query} {where_clause} with params {params}")
                if where_clause:
                    cursor.execute(f"{count_query} {where_clause}", params)
                else:
                    cursor.execute(count_query)
                total_events = cursor.fetchone()[0]

                # Debugging: Print total events
                print(f"Total events count: {total_events}")

                query = f"""
                    {base_query}
                    {where_clause}
                    ORDER BY events.tanggal DESC
                    LIMIT %s OFFSET %s
                """
                # Debugging: Print query untuk pengambilan data events
                print(f"Executing query: {query} with params {params + [per_page, offset]}")
                cursor.execute(query, params + [per_page, offset])
                results = cursor.fetchall()

                events_list = []
                for row in results:
                    events_list.append({
                        "id": row[0],
                        "gambar": row[1],
                        "nama": row[2],
                        "deskripsi": row[3],
                        "tanggal": row[4].strftime('%Y-%m-%d'),
                        "lokasi": row[5],
                        "user_id": row[6],  # ID user yang memiliki event
                        "username": row[7]   # Nama pengguna yang memiliki event
                    })

        total_pages = (total_events + per_page - 1) // per_page

        # Debugging: Print hasil akhir
        print(f"Returning response with {len(events_list)} events on page {page}")

        return jsonify({
            "current_page": page,
            "per_page": per_page,
            "total_events": total_events,
            "total_pages": total_pages,
            "events": events_list
        }), 200

    except Exception as e:
        # Debugging: Print exception error
        print(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@events_endpoints.route('/manage', methods=['GET'])
@jwt_required()
def get_admin_events():
    """Endpoint to get all events managed by the logged-in user (only accessible by admin)."""
    try:
        # Ambil data dari JWT untuk verifikasi pengguna
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles() 

        # Pastikan pengguna adalah admin
        if 'admin' not in user_roles:
            return jsonify({"message": "Access denied. Admins only."}), 403

        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search_query = request.args.get('search', '').strip()
        offset = (page - 1) * per_page

        # Debugging: Print admin info and parameters
        print(f"Admin ID: {user_id}, Roles: {user_roles}, Page: {page}, Per Page: {per_page}, Search Query: '{search_query}'")

        with get_connection() as connection:
            with connection.cursor() as cursor:
                base_query = """
                    SELECT events.id, events.gambar, events.nama, events.deskripsi, events.tanggal, events.lokasi, events.user_id, user.username
                    FROM events
                    LEFT JOIN user ON events.user_id = user.id
                    WHERE events.user_id = %s
                """
                count_query = "SELECT COUNT(*) FROM events WHERE events.user_id = %s"
                where_clause = ""
                params = [user_id]

                # Add search query filtering
                if search_query:
                    where_clause = "AND (events.nama LIKE %s OR events.deskripsi LIKE %s)"
                    params.extend([f"%{search_query}%", f"%{search_query}%"])

                # Debugging: Print query and parameters
                print(f"Search Query: '{search_query}' -> WHERE Clause: {where_clause} with Params {params}")

                # Count total events for pagination
                cursor.execute(f"{count_query} {where_clause}", params)
                total_events = cursor.fetchone()[0]

                # Debugging: Print total events count
                print(f"Total events count: {total_events}")

                # Fetch events data with pagination
                query = f"""
                    {base_query}
                    {where_clause}
                    ORDER BY events.tanggal DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(query, params + [per_page, offset])
                results = cursor.fetchall()

                events_list = []
                for row in results:
                    events_list.append({
                        "id": row[0],
                        "gambar": row[1],
                        "nama": row[2],
                        "deskripsi": row[3],
                        "tanggal": row[4].strftime('%Y-%m-%d'),
                        "lokasi": row[5],
                        "user_id": row[6],  # ID user who owns the event
                        "username": row[7]   # Username of the event owner
                    })

        total_pages = (total_events + per_page - 1) // per_page

        # Debugging: Print final response data
        print(f"Returning response with {len(events_list)} events for Admin ID {user_id} on Page {page}")

        return jsonify({
            "current_page": page,
            "per_page": per_page,
            "total_events": total_events,
            "total_pages": total_pages,
            "events": events_list
        }), 200

    except Exception as e:
        # Debugging: Print exception error
        print(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

# Get event by ID
@events_endpoints.route('/events/<int:event_id>', methods=['GET'])
def get_event_by_id(event_id):
    """Endpoint to get a specific event by its ID"""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Ambil data event berdasarkan ID beserta info user yang memiliki event
                cursor.execute("""
                    SELECT e.id, e.gambar, e.nama, e.deskripsi, e.tanggal, e.lokasi, e.user_id, u.username
                    FROM events e
                    LEFT JOIN user u ON e.user_id = u.id
                    WHERE e.id = %s
                """, (event_id,))
                result = cursor.fetchone()

                # Jika data ditemukan, format menjadi dictionary
                if result:
                    event_data = {
                        "id": result[0],
                        "gambar": result[1],
                        "nama": result[2],
                        "deskripsi": result[3],
                        "tanggal": result[4].strftime('%Y-%m-%d'),  # Format tanggal
                        "lokasi": result[5], 
                        "user_id": result[6],  # ID pengguna yang memiliki event
                        "username": result[7]  # Nama pengguna yang memiliki event
                    }
                    return jsonify({"event": event_data}), 200
                else:
                    # Jika event dengan ID tidak ditemukan
                    return jsonify({"message": "Event not found"}), 404

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

#Add Events
@events_endpoints.route('/add', methods=['POST'])
@jwt_required()
def add_event():
    """Endpoint to add a new event (only accessible by admin)."""
    try:
        # Ambil data dari JWT untuk verifikasi pengguna
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles()  # Ambil roles pengguna dari JWT

        # Pastikan pengguna adalah admin
        if 'admin' not in user_roles:
            return jsonify({"message": "You must be an admin to add events."}), 403

        # Ambil parameter form dari request
        nama = request.form.get('nama')
        deskripsi = request.form.get('deskripsi')
        tanggal = request.form.get('tanggal')
        lokasi = request.form.get('lokasi')
        gambar = request.files.get('gambar')

        if not all([nama, deskripsi, tanggal, lokasi, gambar]):
            return jsonify({"message": "All fields are required."}), 400

        # Generate a new filename for the event image
        try:
            # Generate a unique filename using event details and preserve the original extension
            unique_id = uuid.uuid4().hex
            file_extension = os.path.splitext(gambar.filename)[1]
            new_filename = f"{unique_id}{file_extension}"
            file_path = os.path.join(UPLOAD_FOLDER, new_filename)

            # Ensure the directory exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            # Log the file path for debugging
            current_app.logger.debug(f"Saving new event image to {file_path}")

            # Save the new event image
            gambar.save(file_path)
            current_app.logger.debug(f"Saved new event image successfully.")
        except Exception as e:
            current_app.logger.error(f"Error handling event image upload: {e}")
            return jsonify({"message": "Error handling event image upload.", "error": str(e)}), 500

        # Insert event data into the database
        with get_connection() as connection:
            with connection.cursor() as cursor:
                insert_query = """
                    INSERT INTO events (user_id, nama, deskripsi, tanggal, lokasi, gambar)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (user_id, nama, deskripsi, tanggal, lokasi, new_filename))
                connection.commit()

                # Cek apakah data berhasil dimasukkan
                if cursor.rowcount > 0:
                    return jsonify({"message": "Event added successfully."}), 201
                else:
                    return jsonify({"message": "Failed to add event."}), 500

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

#Update Events
@events_endpoints.route('/update/<int:event_id>', methods=['POST'])
@jwt_required()
def update_event(event_id):
    """Endpoint to update an event (only accessible by admin and the event owner)."""
    try:
        # Ambil data dari JWT untuk verifikasi pengguna
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles()  # Ambil roles pengguna dari JWT

        # Pastikan pengguna adalah admin
        if 'admin' not in user_roles:
            return jsonify({"message": "You must be an admin to update events."}), 403

        # Pastikan pengguna juga pemilik event
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM events WHERE id=%s", (event_id,))
                result = cursor.fetchone()
                if not result or result[0] != user_id:
                    return jsonify({"message": "You are not authorized to edit this event."}), 403

        # Ambil parameter form dari request
        nama = request.form.get('nama')
        deskripsi = request.form.get('deskripsi')
        tanggal = request.form.get('tanggal')
        lokasi = request.form.get('lokasi')
        gambar = request.files.get('gambar')

        if not any([nama, deskripsi, tanggal, lokasi, gambar]):
            return jsonify({"message": "No fields provided for update."}), 400

        fields_to_update = []
        values_to_update = []

        if nama:
            fields_to_update.append("nama=%s")
            values_to_update.append(nama)
        if deskripsi:
            fields_to_update.append("deskripsi=%s")
            values_to_update.append(deskripsi)
        if tanggal:
            fields_to_update.append("tanggal=%s")
            values_to_update.append(tanggal)
        if lokasi:
            fields_to_update.append("lokasi=%s")
            values_to_update.append(lokasi)

        if gambar and gambar.filename != '':
            try:
                # Retrieve current event image from database
                with get_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT gambar FROM events WHERE id=%s", (event_id,))
                        result = cursor.fetchone()
                        current_event_image = result[0] if result else None

                # Generate a new filename using event_id, a unique identifier, and preserve the original extension
                unique_id = uuid.uuid4().hex  # Generate a unique identifier
                file_extension = os.path.splitext(gambar.filename)[1]
                new_filename = f"{event_id}_{unique_id}{file_extension}"
                file_path = os.path.join(UPLOAD_FOLDER, new_filename)

                # Ensure the directory exists
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                # Log the file path for debugging
                current_app.logger.debug(f"Saving new event image to {file_path}")

                # Delete the old event image if it exists
                if current_event_image:
                    old_file_path = os.path.join(UPLOAD_FOLDER, current_event_image)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                        current_app.logger.debug(f"Deleted old event image at {old_file_path}")

                # Save the new event image
                gambar.save(file_path)
                current_app.logger.debug(f"Saved new event image successfully.")

                fields_to_update.append("gambar=%s")
                values_to_update.append(new_filename)
            except Exception as e:
                current_app.logger.error(f"Error handling event image upload: {e}")
                return jsonify({"message": "Error handling event image upload.", "error": str(e)}), 500

        if fields_to_update:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    update_query = f"UPDATE events SET {', '.join(fields_to_update)} WHERE id=%s"
                    values_to_update.append(event_id)

                    cursor.execute(update_query, values_to_update)
                    connection.commit()
                    rows_affected = cursor.rowcount

                    if rows_affected > 0:
                        return jsonify({"event_id": event_id, "message": "Event updated successfully."}), 200
                    else:
                        return jsonify({"message": "Event not found or update failed."}), 404

        return jsonify({"message": "No valid fields provided for update."}), 400

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

#Delete Events
@events_endpoints.route('/delete/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    """Endpoint to delete a specific event (only accessible by admin and event owner)."""
    try:
        # Ambil data dari JWT untuk verifikasi pengguna
        current_user = get_jwt_identity()
        user_id = current_user['id']
        user_roles = get_roles()  # Ambil roles pengguna dari JWT

        # Verifikasi apakah pengguna adalah admin
        if 'admin' not in user_roles:
            return jsonify({"message": "You do not have permission to delete this event."}), 403

        # Verifikasi apakah pengguna adalah pemilik event
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id FROM events WHERE id = %s", (event_id,))
                event_owner = cursor.fetchone()

                # Cek apakah pengguna adalah pemilik event
                if event_owner and event_owner[0] == user_id:
                    # Jika admin dan pemilik acara, lanjutkan dengan penghapusan event
                    cursor.execute("SELECT gambar FROM events WHERE id = %s", (event_id,))
                    event_data = cursor.fetchone()

                    if event_data:
                        event_image = event_data[0]
                        # Hapus gambar dari filesystem jika ada
                        if event_image:
                            file_path = os.path.join(UPLOAD_FOLDER, event_image)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                current_app.logger.debug(f"Deleted event image at {file_path}")

                        # Hapus event dari database
                        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
                        connection.commit()

                        # Cek apakah event berhasil dihapus
                        if cursor.rowcount > 0:
                            return jsonify({"message": "Event deleted successfully."}), 200
                        else:
                            return jsonify({"message": "Event not found."}), 404
                    else:
                        return jsonify({"message": "Event not found."}), 404
                else:
                    return jsonify({"message": "You do not have permission to delete this event."}), 403

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500