"""Routes for module books"""
import os
from flask import Blueprint, jsonify, request
from helper.db_helper import get_connection
from helper.form_validation import get_form_data

tickets_endpoints = Blueprint('tickets', __name__)



# UPLOAD_FOLDER = "img"

# @books_endpoints.route('/read', methods=['GET'])
# def read():
#     """Routes for module get list books"""
#     connection = get_connection()
#     cursor = connection.cursor(dictionary=True)
#     select_query = "SELECT * FROM tb_books"
#     cursor.execute(select_query)
#     results = cursor.fetchall()
#     cursor.close()  # Close the cursor after query execution
#     return jsonify({"message": "OK", "datas": results}), 200

# @books_endpoints.route('/create', methods=['POST'])
# def create():
#     """Routes for module create a book"""
#     required = get_form_data(["title"])  # use only if the field required
#     title = required["title"]
#     description = request.form['description']

#     connection = get_connection()
#     cursor = connection.cursor()
#     insert_query = "INSERT INTO tb_books (title, description) VALUES (%s, %s)"
#     request_insert = (title, description)
#     cursor.execute(insert_query, request_insert)
#     connection.commit()  # Commit changes to the database
#     cursor.close()
#     new_id = cursor.lastrowid  # Get the newly inserted book's ID\
#     if new_id:
#         return jsonify({"title": title, "message": "Inserted", "id_books": new_id}), 201
#     return jsonify({"message": "Cant Insert Data"}), 500

# @books_endpoints.route('/update/<product_id>', methods=['PUT'])
# def update(product_id):
#     """Routes for module update a book"""
#     title = request.form['title']
#     description = request.form['description']

#     connection = get_connection()
#     cursor = connection.cursor()

#     update_query = "UPDATE tb_books SET title=%s, description=%s WHERE id_books=%s"
#     update_request = (title, description, product_id)
#     cursor.execute(update_query, update_request)
#     connection.commit()
#     cursor.close()
#     data = {"message": "updated", "id_books": product_id}
#     return jsonify(data), 200

# @books_endpoints.route('/delete/<product_id>', methods=['GET'])
# def delete(product_id):
#     """Routes for module to delete a book"""
#     connection = get_connection()
#     cursor = connection.cursor()

#     delete_query = "DELETE FROM tb_books WHERE id_books = %s"
#     delete_id = (product_id,)
#     cursor.execute(delete_query, delete_id)
#     connection.commit()
#     cursor.close()
#     data = {"message": "Data deleted", "id_books": product_id}
#     return jsonify(data)

# @books_endpoints.route("/upload", methods=["POST"])
# def upload():
#     """Routes for upload file"""
#     uploaded_file = request.files['file']
#     if uploaded_file.filename != '':
#         file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
#         uploaded_file.save(file_path)
#         return jsonify({"message": "ok", "data": "uploaded", "file_path": file_path}), 200
#     return jsonify({"err_message": "Can't upload data"}), 400
