from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash

db = SQLAlchemy()

# Таблица связи многие-ко-многим для ролей пользователей
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100), nullable=False)
    patronymic = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        name_parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join([p for p in name_parts if p]) or 'Без имени'
    
    def get_role_names(self):
        return [role.name for role in self.roles]
    
    def get_id(self):
        return str(self.id)


class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Role {self.name}>'


def init_db(app):
    """Создание таблиц и добавление тестовых данных"""
    with app.app_context():
        db.create_all()
        
        # Добавляем роли
        if Role.query.count() == 0:
            roles = [
                Role(name='admin', description='Администратор системы'),
                Role(name='user', description='Обычный пользователь'),
                Role(name='moderator', description='Модератор')
            ]
            for role in roles:
                db.session.add(role)
            db.session.commit()
        
        # Добавляем тестового пользователя admin (для ЛР4)
        if User.query.filter_by(username='admin').first() is None:
            admin = User(
                username='admin',
                last_name='Иванов',
                first_name='Иван',
                patronymic='Иванович'
            )
            admin.set_password('Admin123!')
            admin.roles.append(Role.query.filter_by(name='admin').first())
            db.session.add(admin)
            db.session.commit()
        
        # Добавляем тестового пользователя user с паролем qwerty (для ЛР3)
        if User.query.filter_by(username='user').first() is None:
            test_user = User(
                username='user',
                last_name='Петров',
                first_name='Петр',
                patronymic='Петрович'
            )
            test_user.set_password('qwerty')  # Пароль для ЛР3
            test_user.roles.append(Role.query.filter_by(name='user').first())
            db.session.add(test_user)
            db.session.commit()