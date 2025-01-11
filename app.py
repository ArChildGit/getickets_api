"""Small apps to demonstrate endpoints with basic feature - CRUD"""

from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from extensions import jwt
# from api.books.endpoints import books_endpoints
from LATIHAN.authors.endpoints import authors_endpoints
from api.auth.endpoints import auth_endpoints
from api.user.endpoints import user_endpoints
from api.events.endpoints import events_endpoints
from api.packages.endpoints import packages_endpoints
from api.tickets.endpoints import tickets_endpoints
from api.committee.endpoints import committee_endpoints
from api.data_protected.endpoints import protected_endpoints
from config import Config
from static.static_file_server import static_file_server


# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)


jwt.init_app(app)

# register the blueprint
app.register_blueprint(auth_endpoints, url_prefix='/api/v1/auth')
app.register_blueprint(authors_endpoints, url_prefix='/api/v1/authors')
app.register_blueprint(protected_endpoints,
                       url_prefix='/api/v1/protected')
# app.register_blueprint(books_endpoints, url_prefix='/api/v1/books')
app.register_blueprint(user_endpoints, url_prefix='/api/v1/user')
app.register_blueprint(events_endpoints, url_prefix='/api/v1/events')
app.register_blueprint(packages_endpoints, url_prefix='/api/v1/packages')
app.register_blueprint(tickets_endpoints, url_prefix='/api/v1/tickets')
app.register_blueprint(committee_endpoints, url_prefix='/api/v1/committee')
app.register_blueprint(static_file_server, url_prefix='/static/')

if __name__ == '__main__':
    app.run(debug=True)
