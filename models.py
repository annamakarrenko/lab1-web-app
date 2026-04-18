from flask_login import UserMixin

class User(UserMixin):
    """Модель пользователя для Flask-Login"""
    
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password
    
    def get_id(self):
        """Возвращает ID пользователя для Flask-Login"""
        return str(self.id)
    
    @staticmethod
    def get(user_id):
        """Получение пользователя по ID"""
        if user_id == '1':
            return User(1, 'user', 'qwerty')
        return None
    
    @staticmethod
    def find_by_username(username):
        """Поиск пользователя по имени"""
        if username == 'user':
            return User(1, 'user', 'qwerty')
        return None