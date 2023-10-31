from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from website import connect_db
from elasticsearch import Elasticsearch

es = Elasticsearch(['http://localhost:9200'])
db = connect_db()

view = Blueprint('view', __name__)
