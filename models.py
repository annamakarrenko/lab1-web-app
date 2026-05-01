from flask_login import UserMixin
from database import User as DBUser

class User(UserMixin):
    """Обёртка для Flask-Login — использует БД"""
    
    def __init__(self, db_user):
        self.id = str(db_user.id)
        self.username = db_user.username
        self.db_user = db_user
    
    @staticmethod
    def get(user_id):
        """Получение пользователя по ID из БД"""
        from database import User as DBUser
        db_user = DBUser.query.get(int(user_id))
        return User(db_user) if db_user else None
    
    @staticmethod
    def find_by_username(username):
        """Поиск пользователя по имени в БД"""
        from database import User as DBUser
        db_user = DBUser.query.filter_by(username=username).first()
        return User(db_user) if db_user else None
    
    def check_password(self, password):
        """Проверка пароля"""
        return self.db_user.check_password(password)
    
    def get_full_name(self):
        return self.db_user.get_full_name()
    
    def get_primary_role(self):
        return self.db_user.get_primary_role()