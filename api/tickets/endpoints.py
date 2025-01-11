from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import create_access_token, decode_token
from flask_bcrypt import Bcrypt
import os
import uuid
from datetime import timedelta, datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from helper.jwt_helper import get_roles
import traceback

from helper.db_helper import get_connection

bcrypt = Bcrypt()
tickets_endpoints = Blueprint('tickets', __name__)

@tickets_endpoints.route('/tickets/<int:event_id>', methods=['GET'])
def get_event_tickets(event_id):
    """Endpoint to retrieve all tickets for a specific event with filter and paging."""
    try:
        # Ambil parameter query untuk paging dan filtering
        page = int(request.args.get('page', 1))  # Default ke halaman 1 jika tidak ada parameter
        per_page = int(request.args.get('per_page', 10))  # Default 10 tiket per halaman
        search = request.args.get('search', '')  # Pencarian berdasarkan nama pengguna atau email
        status_filter = request.args.get('status', '')  # Filter status tiket, misalnya 'Terpakai' atau 'Belum terpakai'

        offset = (page - 1) * per_page  # Hitung offset berdasarkan halaman yang diminta

        # Menyusun query dasar
        query = """
            SELECT 
                t.id AS ticket_id,
                t.user_id AS ticket_owner_id,
                u.username AS ticket_owner_username,
                u.email AS ticket_owner_email,
                t.package_id,
                p.name AS package_name,
                p.price AS package_price,
                t.purchase_date,
                t.deleted_by,
                t.deleted_at
            FROM tickets t
            JOIN packages p ON t.package_id = p.id
            JOIN events e ON p.id_acara = e.id
            JOIN user u ON t.user_id = u.id
            WHERE e.id = %s
        """
        # Menambahkan pencarian berdasarkan nama pengguna atau email
        if search:
            query += f" AND (u.username LIKE %s OR u.email LIKE %s)"
        
        # Menambahkan filter status tiket (Terpakai atau Belum terpakai)
        if status_filter:
            if status_filter == 'Terpakai':
                query += " AND t.deleted_at IS NOT NULL"
            elif status_filter == 'Belum terpakai':
                query += " AND t.deleted_at IS NULL"

        # Menambahkan pagination dengan LIMIT dan OFFSET
        query += " LIMIT %s OFFSET %s"

        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Menyiapkan parameter query yang sesuai
                params = [event_id]
                if search:
                    params += ['%' + search + '%', '%' + search + '%']
                params += [per_page, offset]

                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                tickets = [
                    {
                        "ticket_id": row[0],
                        "ticket_owner_id": row[1],
                        "ticket_owner_username": row[2],
                        "ticket_owner_email": row[3],
                        "package_id": row[4],
                        "package_name": row[5],
                        "package_price": row[6],
                        "purchase_date": row[7],
                        "deleted_by": row[8],
                        "deleted_at": row[9]
                    }
                    for row in results
                ]

                # Mengambil jumlah total tiket untuk event ini
                count_query = """
                    SELECT COUNT(*) 
                    FROM tickets t
                    JOIN packages p ON t.package_id = p.id
                    JOIN events e ON p.id_acara = e.id
                    WHERE e.id = %s
                """
                cursor.execute(count_query, (event_id,))
                total_count = cursor.fetchone()[0]

        return jsonify({
            "tickets": tickets,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page  # Menghitung total halaman
        }), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@tickets_endpoints.route('/user_tickets', methods=['GET'])
@jwt_required()
def get_user_tickets():
    """Endpoint to retrieve all tickets owned by the current user with search and filter support."""
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))  # Default halaman 1
        per_page = int(request.args.get('per_page', 10))  # Default 10 tiket per halaman
        search = request.args.get('search', '').strip()  # Pencarian berdasarkan event_name, event_description, atau event_date
        status_filter = request.args.get('status', '').strip()  # Filter status tiket
        
        # Get data from JWT for user verification
        current_user = get_jwt_identity()
        user_id = current_user['id']

        if not user_id:
            return jsonify({"message": "User not found."}), 404

        # Build query dynamically
        query = """
            SELECT 
                e.id AS event_id,
                e.gambar AS event_image,
                e.nama AS event_name,
                e.deskripsi AS event_description,
                e.tanggal AS event_date,
                e.lokasi AS event_location,
                p.id AS package_id,
                p.name AS package_name,
                p.tickets_per_package,
                p.total_tickets_available,
                p.price AS package_price,
                t.id AS ticket_id,
                t.purchase_date AS ticket_purchase_date,
                t.deleted_by AS ticket_deleted_by,
                t.deleted_at AS ticket_deleted_at
            FROM tickets t
            JOIN packages p ON t.package_id = p.id
            JOIN events e ON p.id_acara = e.id
            WHERE t.user_id = %s
        """

        # Parameters list
        params = [user_id]

        # Apply search filter (based on event_name, event_description, or event_date)
        if search:
            query += " AND (e.nama ILIKE %s OR e.deskripsi ILIKE %s OR e.tanggal::text ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        # Apply status filter
        if status_filter:
            if status_filter.lower() == "terpakai":
                query += " AND t.deleted_at IS NOT NULL"
            elif status_filter.lower() == "belum terpakai":
                query += " AND t.deleted_at IS NULL"

        # Pagination
        query += " ORDER BY t.purchase_date DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])

        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Get the total count of tickets for pagination
                count_query = """
                    SELECT COUNT(*)
                    FROM tickets t
                    JOIN packages p ON t.package_id = p.id
                    JOIN events e ON p.id_acara = e.id
                    WHERE t.user_id = %s
                """
                cursor.execute(count_query, (user_id,))
                total_count = cursor.fetchone()[0]

                # Execute the main query for tickets
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()

                tickets = [
                    {
                        "event_id": row[0],
                        "event_image": row[1],
                        "event_name": row[2],
                        "event_description": row[3],
                        "event_date": row[4],
                        "event_location": row[5],
                        "package_id": row[6],
                        "package_name": row[7],
                        "tickets_per_package": row[8],
                        "total_tickets_available": row[9],
                        "package_price": row[10],
                        "ticket_id": row[11],
                        "ticket_purchase_date": row[12],
                        "ticket_deleted_by": row[13],
                        "ticket_deleted_at": row[14]
                    }
                    for row in results
                ]

        return jsonify({
            "tickets": tickets,
            "page": page,
            "per_page": per_page,
            "total_count": total_count
        }), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@tickets_endpoints.route('/buy-ticket/<int:event_id>', methods=['POST'])
@jwt_required()
def buy_ticket(event_id):
    """Endpoint for users to buy a ticket for an event."""
    try:
        current_user = get_jwt_identity()
        user_id = current_user['id']
        package_id = request.form.get('package_id')  # Ambil package_id dari request

        if not package_id:
            return jsonify({"message": "You haven't specified the package you want to buy."}), 400

        purchase_date = datetime.now()

        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Ambil jumlah tiket yang tersedia untuk paket ini
                cursor.execute("SELECT total_tickets_available FROM packages WHERE id = %s", (package_id,))
                package = cursor.fetchone()

                if not package:
                    return jsonify({"message": "Package not found."}), 404

                total_tickets_available = package[0]
                
                if total_tickets_available < 1:
                    return jsonify({"message": "No tickets available."}), 400

                # Masukkan satu tiket ke dalam tabel
                insert_query = """
                    INSERT INTO tickets (user_id, package_id, purchase_date)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(insert_query, (user_id, package_id, purchase_date))

                # Kurangi total_tickets_available hanya 1
                update_query = """
                    UPDATE packages 
                    SET total_tickets_available = total_tickets_available - 1
                    WHERE id = %s
                """
                cursor.execute(update_query, (package_id,))

                connection.commit()

                return jsonify({"message": "Successfully purchased 1 ticket."}), 201

    except Exception as e:
        print("Error purchasing ticket:", str(e))
        traceback.print_exc()  # Cetak traceback lengkap ke konsol
        return jsonify({"error": str(e)}), 500

@tickets_endpoints.route('/validate-ticket', methods=['POST'])
@jwt_required()
def validate_ticket():
    """Endpoint for event organizers (panitia) to validate a ticket."""
    try:
        current_user = get_jwt_identity()
        user_id = current_user['id']  # ID user yang ingin memvalidasi tiket
        ticket_id = request.form.get('ticket_id')  # ID tiket yang akan divalidasi

        if not ticket_id:
            return jsonify({"message": "You must provide a ticket_id."}), 400

        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Periksa apakah tiket sudah divalidasi sebelumnya
                check_ticket_query = """
                    SELECT p.id_acara, t.deleted_at
                    FROM tickets t
                    JOIN packages p ON t.package_id = p.id
                    WHERE t.id = %s
                """
                cursor.execute(check_ticket_query, (ticket_id,))
                ticket_result = cursor.fetchone()

                if not ticket_result:
                    return jsonify({"message": "Ticket not found."}), 404

                event_id, deleted_at = ticket_result  # Ambil ID acara dan status validasi tiket

                # Jika tiket sudah divalidasi, tolak permintaan
                if deleted_at is not None:
                    return jsonify({"message": "This ticket has already been validated."}), 400

                # Periksa apakah user adalah panitia dari acara ini
                panitia_query = "SELECT 1 FROM panitia WHERE id_user = %s AND id_acara = %s"
                cursor.execute(panitia_query, (user_id, event_id))
                is_panitia = cursor.fetchone()

                if not is_panitia:
                    return jsonify({"message": "You are not authorized to validate this ticket."}), 403

                # Jika user adalah panitia, validasi tiket dengan menambahkan deleted_by dan deleted_at
                update_query = """
                    UPDATE tickets 
                    SET deleted_by = %s, deleted_at = %s
                    WHERE id = %s
                """
                cursor.execute(update_query, (user_id, datetime.now(), ticket_id))
                connection.commit()

                if cursor.rowcount > 0:
                    return jsonify({"message": "Ticket successfully validated."}), 200
                else:
                    return jsonify({"message": "Failed to validate ticket."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@tickets_endpoints.route('/transfer_ticket', methods=['POST'])
@jwt_required()
def transfer_ticket():
    """Endpoint to transfer a ticket from one user to another."""
    try:
        # Get data from JWT for user verification
        current_user = get_jwt_identity()
        current_user_id = current_user['id']

        # Get the transfer details from the request form
        ticket_id = request.form.get('ticket_id')
        new_user_id = request.form.get('new_user_id')

        if not ticket_id or not new_user_id:
            return jsonify({"message": "Ticket ID and new user ID are required."}), 400

        # Verify if the current user is the owner of the ticket and if it is valid
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT user_id, deleted_at 
                    FROM tickets 
                    WHERE id = %s
                """, (ticket_id,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({"message": "Ticket not found."}), 404

                ticket_owner_id, deleted_at = result
                
                if ticket_owner_id != current_user_id:
                    return jsonify({"message": "You are not the owner of this ticket."}), 403

                if deleted_at is not None:
                    return jsonify({"message": "This ticket has already been validated and cannot be transferred."}), 400

                # Check if the new user exists
                cursor.execute("SELECT id FROM user WHERE id = %s", (new_user_id,))
                new_user_result = cursor.fetchone()

                if not new_user_result:
                    return jsonify({"message": "New user not found."}), 404

                # Update the ticket owner to the new user
                cursor.execute("""
                    UPDATE tickets 
                    SET user_id = %s
                    WHERE id = %s
                """, (new_user_id, ticket_id))
                connection.commit()

        return jsonify({"message": "Ticket transferred successfully."}), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500

@tickets_endpoints.route('/delete_ticket', methods=['DELETE'])
@jwt_required()
def delete_ticket():
    """Endpoint to permanently delete a ticket if the user owns it."""
    try:
        # Ambil data pengguna dari JWT
        current_user = get_jwt_identity()
        current_user_id = current_user['id']

        # Ambil ticket_id dari request
        ticket_id = request.form.get('ticket_id')

        if not ticket_id:
            return jsonify({"message": "Ticket ID is required."}), 400

        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Cek apakah tiket ada dan milik pengguna saat ini
                cursor.execute("""
                    SELECT user_id FROM tickets WHERE id = %s
                """, (ticket_id,))
                result = cursor.fetchone()

                if not result:
                    return jsonify({"message": "Ticket not found."}), 404

                ticket_owner_id = result[0]

                if ticket_owner_id != current_user_id:
                    return jsonify({"message": "You are not the owner of this ticket."}), 403

                # Hapus tiket secara permanen dari database
                cursor.execute("DELETE FROM tickets WHERE id = %s", (ticket_id,))
                connection.commit()

        return jsonify({"message": "Ticket deleted permanently."}), 200

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({"message": "An unexpected error occurred.", "error": str(e)}), 500
