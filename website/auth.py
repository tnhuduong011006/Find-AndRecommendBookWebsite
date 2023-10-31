from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, send_file, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson.objectid import ObjectId
from website import connect_db
import website.preprocessing.func as func
import bson
from .models import User
from bson.json_util import dumps
from functools import wraps
import pandas as pd
from datetime import datetime
from elasticsearch import Elasticsearch
import requests
# Tạo một kết nối đến máy chủ Redis
User = User()

# Kết nối đến Elasticsearch
ES_ENDPOINT = "http://nhuduong:abc123@localhost:9200"
es = Elasticsearch(ES_ENDPOINT)

db = connect_db()

auth = Blueprint('auth', __name__)

# Decorators
def login_required(roles=None):
    def decorator(f):
        @wraps(f)
        def wrap(*args, **kwargs):
            session_id = request.cookies.get('user_session')
            if session_id:
                user = db.users.find_one({'_id': ObjectId(session_id)})
                print("User ID :", session_id)
                User.start_session(user)
            else:
                print("dialogflow")
            
            print("User: ", User.get_data("quyen"))
            if roles is None or User.get_data("quyen") in roles:
                return f(*args, **kwargs)
            return redirect('/')
        return wrap
    return decorator

@auth.route('/', methods=['GET'])
def home():
    # session_id = request.cookies.get('user_session')
    # print("session_id_home", session_id)
    # quyen = User.get_data("quyen")
    # print("quyền", quyen)
    # if quyen =="ADMIN":
    #     return redirect(url_for('auth.admin_page'))
    # if quyen =="BASIC":
    #     return redirect(url_for("auth.user_page"))
    return render_template("home.html")


@ auth.route('/admin', methods=['GET', 'POST'])
@ login_required(roles=["ADMIN"])
def admin_page():
    return render_template("admin_page.html")

# Home của user

@ auth.route('/user', methods=['GET', 'POST'])
@ login_required(roles=["BASIC", "ADMIN"])
def users_page():
    quyen = User.get_data("quyen")
    return render_template("user_page.html", quyen = quyen)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mssv = request.form.get('mssv')
        password = request.form.get('password')

        user = db.users.find_one({'mssv': mssv})
        if user and check_password_hash(user['matkhau'], password):
            # flash('Đăng nhập thành công!', category='success')
            # Bắt đầu phiên người dùng
            # session_id = request.cookies.get('user_session')
            # print("START: ", session_id)
            if user['quyen'] == "ADMIN":
                # Set cookie
                response = make_response(redirect(url_for('auth.admin_page')))
                # Không đặt path Cookie sẽ có tác dụng trên toàn bộ route
                response.set_cookie('user_session', str(user["_id"]))
                session_id = request.cookies.get('user_session')
                print("sesion_id_login: ", session_id)
                return response
            else:
                # Set cookie
                response = make_response(redirect(url_for('auth.user_page')))
                response.set_cookie('user_session', str(user["_id"]))
                return response
        else:
            flash('Sai MSSV hoặc mật khẩu!', category='error')

    return render_template("login.html")


def search_elasticsearch(query):
    results = []
    try:
        response = es.search(index='books', body=query)
        hits = response['hits']['hits']
        for hit in hits:
            add_id = {}
            add_id.update({"_id": hit['_id']})
            add_id.update(hit['_source'])
            # print(add_id)
            results.append(add_id)
    except Exception as e:
        print("Error:", e)
    return results

# Láy giá trị duy nhất của một trường


def unique_elasticsearch(query):
    results = []
    try:
        response = es.search(index='books', body=query)
        buckets = response['aggregations']["unique_values"]['buckets']
        for bucket in buckets:
            results.append(bucket["key"])
    except Exception as e:
        print("Error:", e)
    return results

# Xóa các trường trống trong dict


def handleEmptyDict(dic):
    keys = []
    for key in dic:
        if dic[key] == "":
            keys.append(key)
    for key in keys:
        del dic[key]

    return dic


def init_multi_match(query):
    # Truy vấn Elasticsearch với từ khóa bất kỳ
    # multi_match chỉ trả về kết quả cho trường kiểu mapping text và keyword
    # multi_match không tách từ tìm theo match_phrase sử dụng "type" : "phrase"
    multi_match = {
        "multi_match": {
            "query": query,
            "fields": ["TacGia", "TenSach", "ChuDe", "NXB", "LoaiSach"],
            "type": "phrase"
        }
    }

    return multi_match


@ auth.route('/user/search-fast', methods=['GET', 'POST'])
@ login_required(roles=["BASIC", "ADMIN"])
def user_page():
    if request.method == 'GET' and len(request.args) != 0:
        field = request.args.get('selectField')
        query = request.args.get('keyword')
        print(field)
        print(query)

        if field == "key":
            es_query = {
                "_source": True,
                "query":  init_multi_match(query)
            }
        else:
            # Truy vấn Elasticsearch với trường cố định
            es_query = {
                "_source": True,
                "query": {
                    "match_phrase": {
                        field: query
                    }
                }
            }

        elasticsearch_results = search_elasticsearch(es_query)
        return render_template('search_fast.html', results_elasticsearch=elasticsearch_results)
    return render_template('search_fast.html')

# Chuyển đổi dict thành danh sách các điều kiện match

# Match áp dụng tìm kiếm tương đối, sử dụng tokenization
# Term áp dụng tìm kiếm chính xác, không biến đổi văn bản


def convert_match(search_conditions, option):
    should_conditions = []
    for field, value in search_conditions.items():
        if value:
            should_conditions.append({option: {field: value}})

    return should_conditions


@ auth.route('/user/search-multi', methods=['GET', 'POST'])
@ login_required(roles=["BASIC", "ADMIN"])
def user_search_page():
    es_query = {
        "size": 0,
        "aggs": {
            "unique_values": {
                "terms": {
                    "field": "LoaiSach"
                }
            }
        }
    }
    # Get unique của một trường
    types = unique_elasticsearch(es_query)

    if request.method == 'GET' and len(request.args) != 0:
        search_conditions = {
            "TenSach": request.args.get('TenSach'),
            "ChuDe": request.args.get('ChuDe'),
            "TacGia": request.args.get('TacGia'),
            "LoaiSach": request.args.get('selectType'),
            "STTKe": request.args.get('STTKe'),
            "NXB": request.args.get('NXB'),
            "NamXB": request.args.get('NamXB')
        }
        '''Quá trình xử lý truy vấn'''
        search_conditions = handleEmptyDict(search_conditions)
        # Chuyển đổi dict thành danh sách các điều kiện match
        should_conditions = convert_match(search_conditions, "match_phrase")
        print(should_conditions)
        # must + term = and tìm kiếm chính xác
        dictt = {
            "must": should_conditions
        }
        # Truy vấn Elasticsearch nhiều field
        es_query = {
            "_source": True,
            "query": {
                "bool": dictt
            }
        }
        print(es_query)

        elasticsearch_results = search_elasticsearch(es_query)
        return render_template('search_multi.html', types=types, results_elasticsearch=elasticsearch_results)

    return render_template('search_multi.html', types=types)


@ auth.route('/user/search-enhance', methods=['GET', 'POST'])
@ login_required(roles=["BASIC", "ADMIN"])
def user_search_enhance():

    if request.method == 'GET' and len(request.args) != 0:
        dicct = {
            "must": [],
            "should": [],
            "must_not": []
        }
        search_conditions = {
            request.args.get('formControlSelect1'): request.args.get('keyword1'),
            request.args.get('formControlSelect2'): request.args.get('keyword2'),
            request.args.get('formControlSelect3'): request.args.get('keyword3')
        }

        print(search_conditions)
        # Vừa lấy index, vừa lấy (key, value) của dict
        for index, (field, value) in enumerate(search_conditions.items()):
            if value != "":
                if field == all:
                    dicct["must"] += init_multi_match(value)
                else:
                    condd = "conditionSelect" + str(index+1)
                    dicct[request.args.get(
                        condd)] += convert_match({field: value}, "match_phrase")

        es_query = {
            "_source": True,
            "query": {
                "bool": dicct
            }
        }
        elasticsearch_results = search_elasticsearch(es_query)
        return render_template('search_enhance.html', results_elasticsearch=elasticsearch_results, es=es_query)

    return render_template('search_enhance.html')


@auth.route('/user/search-history', methods=['GET'])
@ login_required(roles=["BASIC", "ADMIN"])
def search_history():
    session_id = request.cookies.get('user_session')
    result = db.users.find_one({'_id': ObjectId(User.get_data("_id"))})
    print(result)
    if result.get("history") is not None:
        return render_template('search_history.html', history=result['history'], message="")

    return render_template('search_history.html', message="Lịch sử tìm kiếm trống !!!")


'''DIALOGFLOW'''

dic_search = {} 

@auth.route('/user/dialogflow', methods=['GET', 'POST'])
@ login_required(roles=["BASIC", "ADMIN"])
def handle_request():
    user_id = User.get_data("_id")
    global dic_search
    # Retrieve the JSON data from the request
    payload = request.get_json()
    # print("--", payload)

    # Extract the necessary information from the payload
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    queryText = payload['queryResult']['queryText']
    # output_contexts = payload['queryResult']['outputContexts']
    # r_id = extract_r_id(output_contexts[0]["name"])
    if (intent == "book.search") and parameters["book-fields"]:
        for i in parameters["book-fields"]:
            dic_search.update({i:  queryText})
        print(dic_search)
        return jsonify({
            "fulfillmentText": dic_search
        })

    if intent == "book.search.complete":
        '''Quá trình xử lý truy vấn'''
        search_conditions = handleEmptyDict(dic_search)
        dic_search = {}
        # Tìm kiếm chính xác với tùy chọn tokenization
        should_conditions = convert_match(search_conditions, "match")
        print(should_conditions)
        # must + term = and tìm kiếm chính xác
        dictt = {
            "must": should_conditions
        }
        # Truy vấn Elasticsearch nhiều field
        es_query = {
            "_source": True,
            "query": {
                "bool": dictt
            }
        }
        print(es_query)

        elasticsearch_results = search_elasticsearch(es_query)

        button_list = []
        for index, i in enumerate(elasticsearch_results):
            link_book = "/user/book/"+i['_id']
            one_button = {
                "type": "button",
                "icon": {
                    "type": "chevron_right",
                    "color": "#FF9800"
                },
                "text":  str(index+1) + ". " + i["TenSach"],
                "link": link_book,
                "event": {
                    "name": "",
                    "languageCode": "",
                    "parameters": {}
                }
            }

            button_list.append(one_button)

        result = {
            "fulfillmentMessages": [
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "description",
                                    "title": "Có " + str(len(elasticsearch_results)) + " kết quả được tìm thấy!"
                                }
                            ],
                            button_list
                        ]
                    }
                }
            ]}

        return jsonify(result)

    if intent == "book.history":
        result = db.users.find_one({'_id': ObjectId(user_id)})
        # print(result)
        if result.get("history") is not None:
            button_list = []
            for index, i in enumerate(result['history']):
                link_book = "/user/book/"+i['id']
                one_button = {
                    "type": "button",
                    "icon": {
                        "type": "chevron_right",
                        "color": "#FF9800"
                    },
                    "text":  str(index+1) + ". " + i["name"],
                    "link": link_book,
                    "event": {
                        "name": "",
                        "languageCode": "",
                        "parameters": {}
                    }
                }

                button_list.append(one_button)

            result = {
                "fulfillmentMessages": [
                    {
                        "payload": {
                            "richContent": [
                                [
                                    {
                                        "type": "description",
                                        "title": "Kết quả 10 tài liệu bạn đã xem gần đây!, nếu muốn hiển thị nhiều tài liệu hơn, bạn có thể truy cập lịch sử tìm kiếm trên thanh menu"
                                    }
                                ],
                                button_list
                            ]
                        }
                    }
                ]}

        return jsonify(
            result
        )
        
@auth.route('/download/<filename>')
def download_file(filename):
    # Đường dẫn tới tệp bạn muốn tải xuống
    file_path = './data/file_example/' + filename
    return send_file(file_path, as_attachment=True)

@ auth.route('/user/book/<id>')
@ login_required(roles=["BASIC", "ADMIN"])
def recommend(id):
    es_query = {
        "_source": True,
        "query": {
            "match": {
                "_id": id
            }
        }
    }

    one_book = search_elasticsearch(es_query)
    print(one_book)
    # Thêm id vào lịch sử tìm kiếm
    current_time = datetime.now()
    # Bỏ phần millisecond
    current_time = current_time.replace(microsecond=0)
    session_id = request.cookies.get('user_session')
    result = db["users"].update_one(
        {"_id": ObjectId(User.get_data("_id"))},
        {"$push": {"history": {
            "id": id, "name": one_book[0]["TenSach"], "time": current_time}}}
    )
    print(result.modified_count, User.get_data("_id"), "")

    # Trả về 5 books
    # Kết quả truy vấn của elasticsearch và mongodb sẽ khác nhau <3
    results = func.total(id)
    results = [row for row in results]

    return render_template('book_detail.html', book=one_book, rs=results)


@ auth.route('/user/logout')
def logout():
    session_id = request.cookies.get('user_session')
    User.signout(session_id)
    return redirect(url_for('auth.login'))


ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def change_password(user):
    print(user['matkhau'])
    user['matkhau'] = generate_password_hash(user['matkhau'], method='sha256')

    return user


@ auth.route('/admin/user/add', methods=['GET', 'POST'])
def user_add():

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Chưa chọn tập tin!', category='error')
        elif request.files['file'].filename == '':
            flash('Không tìm thấy tên tập tin!', category='error')
        elif not allowed_file(request.files['file'].filename):
            flash('Chỉ cho phép file excel!', category='error')
        else:
            file = request.files['file']
            # Đọc nội dung của tệp Excel và chuyển thành DataFrame
            df = pd.read_excel(file)
            print(df.columns)
            col_list = ['email', 'matkhau', 'mssv', 'quyen', 'ten']
            for col in df.columns:
                if col not in col_list:
                    flash('Sai thuộc tính người dùng, vui lòng TẢI FILE MẪU bên dưới để định dạng dữ liệu đúng!', category='error')
                    return render_template('admin_upload_users.html')
            # Tạo List các document
            data = df.to_dict('records')
            data = list(map(change_password, data))

            if isinstance(data, list):
                result = db['users'].insert_many(data)
                message = f'Thông báo: {len(result.inserted_ids)} người dùng đăng ký thành công'
                print(dir(result))
                flash(message)
            else:
                flash('Định dạng của dữ liệu không phù hợp!')

    return render_template('admin_upload_users.html')


@ auth.route('/admin/user/preview', methods=['GET', 'POST'])
def user_preview():

    if request.method == 'POST':

        if 'file' not in request.files:
            flash('Chưa chọn tập tin!', category='error')
        elif request.files['file'].filename == '':
            flash('Không tìm thấy tên tập tin!', category='error')
        elif not allowed_file(request.files['file'].filename):
            flash('Chỉ cho phép file excel!', category='error')
        else:
            file = request.files['file']
            # Đọc nội dung của tệp Excel và chuyển thành DataFrame
            excel_data = pd.read_excel(file)
            # Tạo List các document
            data = excel_data.to_dict('records')
            return render_template('preview_users.html', data=data)

    return render_template('admin_upload_users.html')

# Thêm Books bằng file excel


@ auth.route('/admin/book/add', methods=['GET', 'POST'])
def book_add():

    if request.method == 'POST':

        if 'file' not in request.files:
            flash('Chưa chọn tập tin!', category='error')
        elif request.files['file'].filename == '':
            flash('Không tìm thấy tên tập tin!', category='error')
        elif not allowed_file(request.files['file'].filename):
            flash('Chỉ chấp nhận file excel!', category='error')
        else:
            file = request.files['file']
            # Đọc nội dung của tệp Excel và chuyển thành DataFrame
            # Các trường có thể thiếu nhưng không được phép sai
            df = pd.read_excel(file)
            print(df.columns)
            col_list = ['ChuDe', 'LoaiSach', 'NXB', 'NamXB', 'STTKe', 'TacGia', 'TenSach', 'TomTat']
            for col in df.columns:
                if col not in col_list:
                    flash('Sai thuộc tính sách, vui lòng TẢI FILE MẪU bên dưới để định dạng dữ liệu đúng!', category='error')
                    return render_template('admin_upload_books.html')
                            
            # excel_data có dạng dataframe
            df["Tags"] = func.create_tags(df)
            print(df.columns)
            # Để chèn vào elasticsearch bắt buộc các trường dữ liệu phải khác NaN
            df = df.fillna(" ")
            # Tạo List các document
            data = df.to_dict('records')

            if isinstance(data, list):
                result = db['books'].insert_many(data)
                message = f'Thông báo: {len(result.inserted_ids)} tài liệu được thêm thành công'
                # Thêm các sách mới vào elastic
                # Lấy danh sách _id của các tài liệu đã được chèn
                inserted_ids = result.inserted_ids
                # Tạo truy vấn tìm kiếm dựa trên danh sách _id
                query = {"_id": {"$in": inserted_ids}}
                # Thực hiện truy vấn
                mongo_data = db['books'].find(query)
                # Đưa dữ liệu vào Elasticsearch
                index_name = 'books'

                for document in mongo_data:
                    # Chuyển đổi dữ liệu từ MongoDB thành định dạng JSON
                    json_data = {
                        "ChuDe": document["ChuDe"],
                        "LoaiSach": document["LoaiSach"],
                        "NXB": document["NXB"],
                        "STTKe": document["STTKe"],
                        "TacGia": document["TacGia"],
                        "TenSach": document["TenSach"],
                        "NamXB": document["NamXB"],
                        "TomTat": document["TomTat"]
                        # Thêm các trường khác tùy theo cấu trúc dữ liệu
                    }

                    # Gửi yêu cầu POST để thêm dữ liệu vào Elasticsearch
                    response = es.index(
                        id=document["_id"], index=index_name, body=json_data)
                flash(message)
            else:
                flash('Định dạng của dữ liệu không phù hợp!')

    return render_template('admin_upload_books.html')


@ auth.route('/admin/book/preview', methods=['GET', 'POST'])
def book_preview():

    if request.method == 'POST':

        if 'file' not in request.files:
            flash('Chưa chọn tập tin!', category='error')
        elif request.files['file'].filename == '':
            flash('Không tìm thấy tên tập tin!', category='error')
        elif not allowed_file(request.files['file'].filename):
            flash('Chỉ cho phép file excel!', category='error')
        else:
            file = request.files['file']
            # Đọc nội dung của tệp Excel và chuyển thành DataFrame
            excel_data = pd.read_excel(file)
            # Tạo List các document
            data = excel_data.to_dict('records')
            return render_template('preview_books.html', data=data)

    return render_template('admin_upload_books.html')
