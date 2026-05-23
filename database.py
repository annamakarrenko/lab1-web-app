from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

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
    visits = db.relationship('VisitLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        name_parts = [self.last_name, self.first_name, self.patronymic]
        return ' '.join([p for p in name_parts if p]) or 'Без имени'
    
    def full_name(self):
        return self.get_full_name()
    
    def get_role_names(self):
        return [role.name for role in self.roles]
    
    def get_id(self):
        return str(self.id)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def has_role(self, role_name):
        """проверка наличия роли у пользователя"""
        return any(role.name == role_name for role in self.roles)


class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Role {self.name}>'


class VisitLog(db.Model):
    __tablename__ = 'visit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<VisitLog {self.path} by user {self.user_id}>'


def init_db(app):
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
        
        # Добавляем администратора
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                first_name='Админ',
                last_name='Админ'
            )
            admin.set_password('Admin123!')
            admin.roles.append(Role.query.filter_by(name='admin').first())
            db.session.add(admin)
            db.session.commit()
            print("Администратор создан: admin / Admin123!")
        
        # ДОБАВЛЯЕМ ОБЫЧНОГО ПОЛЬЗОВАТЕЛЯ
        if not User.query.filter_by(username='user').first():
            user = User(
                username='user',
                first_name='Иван',
                last_name='Иванов',
                patronymic='Петрович'
            )
            user.set_password('qwerty')
            user.roles.append(Role.query.filter_by(name='user').first())
            db.session.add(user)
            db.session.commit()
            print("Обычный пользователь создан: user / qwerty")
