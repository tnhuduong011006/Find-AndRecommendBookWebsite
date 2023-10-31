from flask import jsonify, session, redirect
import redis
# Tạo một kết nối đến máy chủ Redis
r = redis.from_url("redis://localhost:6379")

class User:
    
    def __init__(self):
        # Tạo một kết nối đến máy chủ Redis khi khởi tạo đối tượng
        self.r = redis.from_url("redis://localhost:6379")

    # Hàm để đảm bảo việc đóng kết nối Redis khi không cần sử dụng nó nữa
    def __del__(self):
        if hasattr(self, 'r') and self.r is not None:
            self.r.connection_pool.disconnect()
    
    # Các phương thức khác của lớp User ở đây...
  
    # Hàm để thêm dữ liệu vào Redis
    def add_data(self, key, value):
        try:
            r.hmset(key, value)
            return True
        except Exception as e:
            print(f"Lỗi khi thêm dữ liệu: {str(e)}")
            return False

    # Hàm để lấy dữ liệu từ Redis
    def get_data(self, field):
        try:
            value = r.hget("session_info", field)
            if value:
                return value.decode("utf-8")
            else:
                return None
        except Exception as e:
            print(f"Lỗi khi lấy dữ liệu: {str(e)}")
            return None

    # Hàm để xóa dữ liệu từ Redis
    def delete_data(self, key_name):
        try:
            return r.delete(key_name)
        except Exception as e:
            print(f"Lỗi khi xóa dữ liệu: {str(e)}")
            return False
        
    def start_session(self, user):
        info = {
        "_id" : str(user["_id"]),
        "quyen" : user["quyen"],
        "logged_in": 1
        }
        # session_id = user["mssv"]
        self.add_data("session_info", info)
        return user, 200

    def signout(self, session_id):
        self.delete_data(session_id)
        return redirect('/')
