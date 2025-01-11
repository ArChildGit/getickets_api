# """Static endpoint to show image"""
# from flask import Blueprint, send_from_directory

# static_file_server = Blueprint('static_file_server', __name__)
# UPLOAD_FOLDER = 'img'

# @static_file_server.route("/show_image/<image_name>", methods=["GET"])
# def show_image(image_name):
#     """Show file"""
#     return send_from_directory(UPLOAD_FOLDER, image_name)

from flask import Blueprint, send_from_directory, abort
import os

static_file_server = Blueprint('static_file_server', __name__)
UPLOAD_FOLDER = 'img'

@static_file_server.route("/events/<image_name>", methods=["GET"])
def show_event_image(image_name):
    """Show file from the events folder"""
    folder_path = os.path.join(UPLOAD_FOLDER, "events")
    return send_from_directory(folder_path, image_name)

@static_file_server.route("/profile/<image_name>", methods=["GET"])
def show_profile_image(image_name):
    """Show file from the profile folder"""
    folder_path = os.path.join(UPLOAD_FOLDER, "profile")
    return send_from_directory(folder_path, image_name)
