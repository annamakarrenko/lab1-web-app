from flask import Blueprint, render_template, request, make_response
from flask_login import current_user, login_required
from database import db, User, VisitLog
from sqlalchemy import func
import csv
import io

visit_logs = Blueprint('visit_logs', __name__, url_prefix='/visit-logs')


@visit_logs.route('/')
@login_required
def index():
    """Главная страница журнала посещений"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Администратор видит все записи, обычный пользователь только свои
    if current_user.has_role('admin'):
        query = VisitLog.query
    else:
        query = VisitLog.query.filter_by(user_id=current_user.id)
    
    pagination = query.order_by(VisitLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    logs = pagination.items
    
    return render_template('visit_logs/index.html', logs=logs, pagination=pagination)


@visit_logs.route('/page-stats')
@login_required
def page_stats():
    """Статистика по страницам"""
    if current_user.has_role('admin'):
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).group_by(VisitLog.path).order_by(func.count(VisitLog.id).desc()).all()
    else:
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).filter_by(user_id=current_user.id).group_by(VisitLog.path).order_by(func.count(VisitLog.id).desc()).all()
    
    return render_template('visit_logs/page_stats.html', stats=stats)


@visit_logs.route('/user-stats')
@login_required
def user_stats():
    """Статистика по пользователям"""
    if current_user.has_role('admin'):
        # Администратор: группировка по пользователям
        user_stats = db.session.query(
            User.id,
            User.last_name,
            User.first_name,
            User.patronymic,
            func.count(VisitLog.id).label('count')
        ).join(VisitLog, VisitLog.user_id == User.id, isouter=True)\
         .group_by(User.id).order_by(func.count(VisitLog.id).desc()).all()
        
        # Добавляем неаутентифицированных пользователей
        guest_count = VisitLog.query.filter_by(user_id=None).count()
        stats = list(user_stats)
        if guest_count > 0:
            stats.append((None, None, None, None, guest_count))
    else:
        # Обычный пользователь: только свои посещения
        stats = [(
            current_user.id,
            current_user.last_name,
            current_user.first_name,
            current_user.patronymic,
            VisitLog.query.filter_by(user_id=current_user.id).count()
        )]
    
    return render_template('visit_logs/user_stats.html', stats=stats)


@visit_logs.route('/export-page-stats')
@login_required
def export_page_stats():
    """Экспорт статистики по страницам в CSV"""
    if current_user.has_role('admin'):
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).group_by(VisitLog.path).order_by(func.count(VisitLog.id).desc()).all()
    else:
        stats = db.session.query(
            VisitLog.path,
            func.count(VisitLog.id).label('count')
        ).filter_by(user_id=current_user.id).group_by(VisitLog.path).order_by(func.count(VisitLog.id).desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['№', 'Страница', 'Количество посещений'])
    for i, (path, count) in enumerate(stats, 1):
        writer.writerow([i, path, count])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=page_stats.csv'
    return response


@visit_logs.route('/export-user-stats')
@login_required
def export_user_stats():
    """Экспорт статистики по пользователям в CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['№', 'Пользователь', 'Количество посещений'])
    
    if current_user.has_role('admin'):
        stats = db.session.query(
            User.id,
            User.last_name,
            User.first_name,
            User.patronymic,
            func.count(VisitLog.id).label('count')
        ).join(VisitLog, VisitLog.user_id == User.id, isouter=True)\
         .group_by(User.id).order_by(func.count(VisitLog.id).desc()).all()
        
        for i, (uid, last, first, patronymic, count) in enumerate(stats, 1):
            if uid:
                name = f'{last or ""} {first or ""} {patronymic or ""}'.strip()
            else:
                name = 'Неаутентифицированный пользователь'
            writer.writerow([i, name, count])
        
        guest_count = VisitLog.query.filter_by(user_id=None).count()
        if guest_count > 0:
            writer.writerow([len(stats) + 1, 'Неаутентифицированный пользователь', guest_count])
    else:
        user = current_user
        count = VisitLog.query.filter_by(user_id=user.id).count()
        writer.writerow([1, user.get_full_name(), count])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=user_stats.csv'
    return response