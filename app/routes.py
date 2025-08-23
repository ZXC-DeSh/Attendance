from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, CourseForm, MarkAttendanceForm, AssignCourseForm, MessageForm, ResetPasswordForm, NewsForm, ResetPasswordRequestForm
from app.models import User, Course, AttendanceRecord, Message, News
from datetime import datetime, timezone, timedelta
import sqlalchemy as sa
import sqlalchemy.orm as so
from urllib.parse import urlsplit
from app.email import send_password_reset_email

# Вспомогательные функции для оптимизации запросов
def get_user_courses(user, role_type='all'):
    """Получить курсы пользователя в зависимости от роли"""
    if user.role == 'student':
        return user.enrolled_courses if role_type in ['all', 'enrolled'] else []
    elif user.role == 'teacher':
        return user.teaching_courses if role_type in ['all', 'teaching'] else []
    else:  # admin
        return Course.query.all() if role_type in ['all'] else []

def get_stats():
    """Получить статистику системы (кэшируемая функция)"""
    return {
        'total_users': User.query.count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_teachers': User.query.filter_by(role='teacher').count(),
        'total_courses': Course.query.count()
    }

def get_recent_news(limit=5):
    """Получить последние новости"""
    return db.session.query(News).order_by(News.created_at.desc()).limit(limit).all()

def get_group_data(user):
    """Получить данные группы для пользователя"""
    if user.role == 'student':
        # Для студентов показываем курсы, на которые они записаны, и других студентов
        enrolled_courses = user.enrolled_courses
        students = set()
        
        # Получаем всех студентов, записанных на те же курсы
        for course in enrolled_courses:
            course_students = db.session.query(User).join(User.enrolled_courses).filter(
                Course.id == course.id,
                User.role == 'student'
            ).all()
            students.update(course_students)
        
        return {
            'role': 'student',
            'courses': enrolled_courses,
            'students': list(students)
        }
    elif user.role == 'teacher':
        # Для преподавателей показываем курсы, которые они преподают, и студентов
        teaching_courses = user.teaching_courses
        students = set()
        
        # Получаем всех студентов на курсах преподавателя
        for course in teaching_courses:
            course_students = db.session.query(User).join(User.enrolled_courses).filter(
                Course.id == course.id,
                User.role == 'student'
            ).all()
            students.update(course_students)
        
        return {
            'role': 'teacher',
            'courses': teaching_courses,
            'students': list(students)
        }
    else:
        # Для администраторов показываем все курсы и студентов
        return {
            'role': 'admin',
            'courses': db.session.query(Course).all(),
            'students': db.session.query(User).filter(User.role == 'student').all()
        }


@app.route('/')
@app.route('/index')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    
    # Получаем последние новости для всех пользователей
    recent_news = get_recent_news()
    
    # Текущая дата для мини-календаря
    current_date = datetime.now()
    
    if current_user.role == 'student':
        attendance_records_query = sa.select(AttendanceRecord).where(
            AttendanceRecord.student_id == current_user.id
        ).order_by(AttendanceRecord.date.desc())
        attendance_records_pagination = db.paginate(
            attendance_records_query,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            error_out=False
        )
        attendance_records = attendance_records_pagination.items
        next_url = url_for('index', page=attendance_records_pagination.next_num) \
            if attendance_records_pagination.has_next else None
        prev_url = url_for('index', page=attendance_records_pagination.prev_num) \
            if attendance_records_pagination.has_prev else None
        return render_template(
            'index.html',
            title='Главная',
            attendance_records=attendance_records,
            user=current_user,
            next_url=next_url,
            prev_url=prev_url,
            recent_news=recent_news,
            moment=current_date
        )
    else:
        teaching_courses_query = sa.select(Course).join(User.teaching_courses).where(
            User.id == current_user.id
        ).order_by(Course.name)
        teaching_courses_pagination = db.paginate(
            teaching_courses_query,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            error_out=False
        )
        teaching_courses = teaching_courses_pagination.items
        next_url = url_for('index', page=teaching_courses_pagination.next_num) \
            if teaching_courses_pagination.has_next else None
        prev_url = url_for('index', page=teaching_courses_pagination.prev_num) \
            if teaching_courses_pagination.has_prev else None
        return render_template(
            'index.html',
            title='Главная',
            teaching_courses=teaching_courses,
            user=current_user,
            next_url=next_url,
            prev_url=prev_url,
            recent_news=recent_news,
            moment=current_date
        )

@app.route('/admin')
@login_required
def admin_panel():
    """Админ-панель (только для админов)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    # Получаем статистику
    stats = get_stats()
    
    # Получаем всех пользователей (кроме текущего админа)
    users = User.query.filter(User.id != current_user.id).order_by(User.role, User.username).all()
    
    # Получаем все курсы
    courses = Course.query.all()
    
    # Получаем последние новости
    recent_news = get_recent_news(6)
    
    return render_template('admin_panel.html',
                         stats=stats,
                         users=users,
                         courses=courses,
                         recent_news=recent_news)

@app.route('/admin/create_news', methods=['GET', 'POST'])
@login_required
def create_news():
    if not current_user.is_admin():
        flash('У вас нет прав создавать новости.', 'danger')
        return redirect(url_for('index'))
    
    form = NewsForm()
    if form.validate_on_submit():
        news = News(
            title=form.title.data,
            content=form.content.data,
            author_id=current_user.id
        )
        db.session.add(news)
        db.session.commit()
        flash('Новость успешно создана!', 'success')
        return redirect(url_for('admin_panel'))
    
    return render_template('create_news.html', title='Создать новость', form=form)

@app.route('/calendar')
@login_required
def calendar():
    
    # Получаем текущую дату
    current_date = datetime.now()
    
    # Получаем год и месяц из параметров запроса или используем текущие
    year = request.args.get('year', current_date.year, type=int)
    month = request.args.get('month', current_date.month, type=int)
    
    # Валидация месяца и года
    if month < 1 or month > 12:
        month = 1
    if year < 1900 or year > 2100:
        year = current_date.year
    
    # Получаем расписание для текущего пользователя
    user_courses = get_user_courses(current_user)
    schedule_data = {
        'courses': user_courses,
        'role': current_user.role
    }
    
    return render_template('calendar.html',
                         title='Календарь',
                         year=year,
                         month=month,
                         current_date=current_date,
                         schedule_data=schedule_data,
                         datetime=datetime,
                         timedelta=timedelta)

@app.route('/group')
@login_required
def group():
    # Получаем информацию о группе для текущего пользователя
    group_data = get_group_data(current_user)
    
    # Получаем статистику посещаемости для студентов
    attendance_stats = {}
    for student in group_data['students']:
        student_records = db.session.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == student.id
        ).all()
        
        total_records = len(student_records)
        present_records = len([r for r in student_records if r.status == 'present'])
        absent_records = len([r for r in student_records if r.status == 'absent'])
        late_records = len([r for r in student_records if r.status == 'late'])
        
        if total_records > 0:
            attendance_percentage = (present_records / total_records) * 100
        else:
            attendance_percentage = 0
        
        attendance_stats[student.id] = {
            'total': total_records,
            'present': present_records,
            'absent': absent_records,
            'late': late_records,
            'percentage': round(attendance_percentage, 1)
        }
    
    return render_template('group.html',
                         title='Группа',
                         group_data=group_data,
                         attendance_stats=attendance_stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Неверное имя пользователя или пароль', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            if user.is_admin():
                next_page = url_for('admin_panel')
            else:
                next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST']) 
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role=form.role.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Поздравляем, вы зарегистрированы!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    
    if user.role == 'student':
        # Для студентов показываем записи о посещаемости
        attendance_query = sa.select(AttendanceRecord).where(
            AttendanceRecord.student_id == user.id
        ).order_by(AttendanceRecord.date.desc())
        attendance_pagination = db.paginate(
            attendance_query,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            error_out=False
        )
        attendance_records = attendance_pagination.items
        next_url = url_for('user', username=username, page=attendance_pagination.next_num) \
            if attendance_pagination.has_next else None
        prev_url = url_for('user', username=username, page=attendance_pagination.prev_num) \
            if attendance_pagination.has_prev else None
        
        return render_template('user.html', 
                             user=user, 
                             attendance_records=attendance_records,
                             next_url=next_url,
                             prev_url=prev_url)
    else:
        # Для преподавателей показываем курсы, которые они преподают
        teaching_query = sa.select(Course).join(User.teaching_courses).where(
            User.id == user.id
        ).order_by(Course.name)
        teaching_pagination = db.paginate(
            teaching_query,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            error_out=False
        )
        teaching_courses = teaching_pagination.items
        next_url = url_for('user', username=username, page=teaching_pagination.next_num) \
            if teaching_pagination.has_next else None
        prev_url = url_for('user', username=username, page=teaching_pagination.prev_num) \
            if teaching_pagination.has_prev else None
        
        return render_template('user.html', 
                             user=user, 
                             teaching_courses=teaching_courses,
                             next_url=next_url,
                             prev_url=prev_url)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Ваши изменения сохранены.', 'success')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Редактировать профиль', form=form)

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'teacher':
        flash('У вас нет прав создавать курсы.', 'danger')
        return redirect(url_for('index'))
    
    form = CourseForm()
    if form.validate_on_submit():
        try:
            course = Course(name=form.name.data, description=form.description.data)
            # Автоматически назначаем создателя преподавателем курса
            course.teachers.append(current_user)
            db.session.add(course)
            db.session.commit()
            flash('Курс создан успешно!', 'success')
            return redirect(url_for('courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка создания курса: {str(e)}', 'danger')
    
    return render_template('create_edit_course.html', title='Создать курс', form=form)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = db.get_or_404(Course, course_id)
    
    # Администраторы могут редактировать любые курсы
    if current_user.is_admin():
        pass  # Администратор имеет полный доступ
    # Преподаватели могут редактировать только свои курсы
    elif current_user.role == 'teacher':
        if course not in current_user.teaching_courses:
            flash('Вы можете редактировать только свои курсы.', 'danger')
            return redirect(url_for('courses'))
    else:
        flash('У вас нет прав редактировать курсы.', 'danger')
        return redirect(url_for('index'))
    
    form = CourseForm(original_name=course.name)
    
    if form.validate_on_submit():
        try:
            course.name = form.name.data
            course.description = form.description.data
            db.session.commit()
            flash('Курс обновлен успешно!', 'success')
            return redirect(url_for('courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка обновления курса: {str(e)}', 'danger')
    elif request.method == 'GET':
        form.name.data = course.name
        form.description.data = course.description
    
    return render_template('create_edit_course.html', title='Редактировать курс', form=form, course=course)

@app.route('/courses')
@login_required
def courses():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'favorites_first')  # По умолчанию избранные первыми
    filter_favorites = request.args.get('filter_favorites', 'all')
    
    # Базовый запрос курсов
    courses_query = sa.select(Course)
    
    # Применяем поиск
    if search:
        courses_query = courses_query.where(
            sa.or_(
                Course.name.ilike(f'%{search}%'),
                Course.description.ilike(f'%{search}%')
            )
        )
    
    # Применяем фильтр по избранным
    if filter_favorites == 'favorites':
        courses_query = courses_query.where(Course.is_favorite == True)
    elif filter_favorites == 'not_favorites':
        courses_query = courses_query.where(Course.is_favorite == False)
    
    # Применяем сортировку
    if sort_by == 'name':
        courses_query = courses_query.order_by(Course.name)
    elif sort_by == 'name_desc':
        courses_query = courses_query.order_by(Course.name.desc())
    elif sort_by == 'favorites_first':
        # Сначала избранные курсы (по алфавиту), затем обычные (по алфавиту)
        courses_query = courses_query.order_by(Course.is_favorite.desc(), Course.name)
    elif sort_by == 'description':
        courses_query = courses_query.order_by(Course.description)
    else:
        # По умолчанию: избранные первыми, затем по алфавиту
        courses_query = courses_query.order_by(Course.is_favorite.desc(), Course.name)
    
    # Пагинация
    courses_pagination = db.paginate(
        courses_query,
        page=page,
        per_page=16,
        error_out=False
    )
    courses = courses_pagination.items
    next_url = url_for('courses', page=courses_pagination.next_num, search=search, sort_by=sort_by, filter_favorites=filter_favorites) \
        if courses_pagination.has_next else None
    prev_url = url_for('courses', page=courses_pagination.prev_num, search=search, sort_by=sort_by, filter_favorites=filter_favorites) \
        if courses_pagination.has_prev else None
    
    return render_template('courses.html', 
                         title='Курсы',
                         courses=courses,
                         next_url=next_url,
                         prev_url=prev_url,
                         search=search,
                         sort_by=sort_by,
                         filter_favorites=filter_favorites)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    course = db.get_or_404(Course, course_id)
    course_name = course.name
    
    # Только администраторы могут удалять курсы
    if not current_user.is_admin():
        flash('Только администраторы могут удалять курсы.', 'danger')
        return redirect(url_for('courses'))
    
    try:
        # Удаляем связанные записи посещаемости
        AttendanceRecord.query.filter_by(course_id=course.id).delete()
        
        # Удаляем связи many-to-many
        course.teachers.clear()
        course.students.clear()
        
        db.session.delete(course)
        db.session.commit()
        flash(f'Курс "{course_name}" удален успешно!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления курса: {str(e)}', 'danger')
    return redirect(url_for('courses'))

@app.route('/assign_to_course', methods=['GET', 'POST'])
@login_required
def assign_to_course():
    if not (current_user.is_admin() or current_user.role == 'teacher'):
        flash('У вас нет прав назначать пользователей на курсы.', 'danger')
        return redirect(url_for('index'))

    form = AssignCourseForm()
    
    # Получаем всех пользователей и курсы
    users = db.session.query(User).order_by(User.username).all()
    courses = db.session.query(Course).order_by(Course.name).all()
    
    # Устанавливаем choices для формы
    form.user_id.choices = [(u.id, f"{u.username} ({u.role})") for u in users]
    form.course_id.choices = [(c.id, c.name) for c in courses]

    if form.validate_on_submit():
        user = db.session.get(User, form.user_id.data)
        course = db.session.get(Course, form.course_id.data)

        if not user or not course:
            flash('Пользователь или курс не найден.', 'warning')
            return redirect(url_for('assign_to_course'))

        try:
            if user.role == 'teacher':
                # Назначаем преподавателя на курс
                if course not in user.teaching_courses:
                    user.teaching_courses.append(course)
                    db.session.commit()
                    flash(f'Преподаватель {user.username} назначен на курс {course.name}.', 'success')
                else:
                    flash(f'Преподаватель {user.username} уже назначен на курс {course.name}.', 'info')
            elif user.role == 'student':
                # Записываем студента на курс
                if course not in user.enrolled_courses:
                    user.enrolled_courses.append(course)
                    db.session.commit()
                    flash(f'Студент {user.username} записан на курс {course.name}.', 'success')
                else:
                    flash(f'Студент {user.username} уже записан на курс {course.name}.', 'info')
            else:
                flash('Некорректная роль пользователя для назначения.', 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при назначении на курс: {str(e)}', 'danger')
        
        return redirect(url_for('assign_to_course'))
    
    return render_template('assign_to_course.html', title='Назначить на курс', form=form)

@app.route('/api/user_courses_status')
@login_required
def api_user_courses_status():
    # Доступ администраторам и преподавателям
    if not (current_user.is_admin() or current_user.role == 'teacher'):
        return {'error': 'Доступ запрещен'}, 403

    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return {'error': 'user_id обязателен'}, 400

    user = db.session.get(User, user_id)
    if not user:
        return {'error': 'Пользователь не найден'}, 404

    courses = db.session.query(Course).order_by(Course.name).all()

    # Обновляем, чтобы убедиться, что связи загружены
    db.session.refresh(user)

    if user.role == 'teacher':
        assigned_ids = {c.id for c in user.teaching_courses}
    elif user.role == 'student':
        assigned_ids = {c.id for c in user.enrolled_courses}
    else:
        assigned_ids = set()

    result = []
    for c in courses:
        result.append({
            'id': c.id,
            'name': c.name,
            'assigned': c.id in assigned_ids
        })

    return {'courses': result, 'user_role': user.role}

@app.route('/api/toggle_assignment', methods=['POST'])
@login_required
def api_toggle_assignment():
    # Доступ только преподавателям
    if current_user.role != 'teacher':
        return {'error': 'Доступ запрещен'}, 403

    data = request.get_json(silent=True) or request.form
    try:
        user_id = int(data.get('user_id'))
        course_id = int(data.get('course_id'))
    except (TypeError, ValueError):
        return {'error': 'Некорректные параметры'}, 400

    user = db.session.get(User, user_id)
    course = db.session.get(Course, course_id)
    if not user or not course:
        return {'error': 'Пользователь или курс не найден'}, 404

    # Обновляем, чтобы убедиться, что связи загружены
    db.session.refresh(user)

    try:
        if user.role == 'teacher':
            if course in user.teaching_courses:
                user.teaching_courses.remove(course)
                assigned = False
            else:
                user.teaching_courses.append(course)
                assigned = True
        elif user.role == 'student':
            if course in user.enrolled_courses:
                user.enrolled_courses.remove(course)
                assigned = False
            else:
                user.enrolled_courses.append(course)
                assigned = True
        else:
            return {'error': 'Некорректная роль пользователя'}, 400

        db.session.commit()
        return {'ok': True, 'assigned': assigned}
    except Exception as e:
        db.session.rollback()
        return {'error': f'Ошибка обновления: {str(e)}'}, 500

@app.route('/api/set_assignment', methods=['POST'])
@login_required
def api_set_assignment():
    # Доступ только преподавателям
    if current_user.role != 'teacher':
        return {'error': 'Доступ запрещен'}, 403

    data = request.get_json(silent=True) or request.form
    try:
        user_id = int(data.get('user_id'))
        course_id = int(data.get('course_id'))
        desired = data.get('assigned')
        if isinstance(desired, str):
            desired = desired.lower() in ('1', 'true', 'yes', 'on')
        desired_assigned = bool(desired)
    except (TypeError, ValueError):
        return {'error': 'Некорректные параметры'}, 400

    user = db.session.get(User, user_id)
    course = db.session.get(Course, course_id)
    if not user or not course:
        return {'error': 'Пользователь или курс не найден'}, 404

    db.session.refresh(user)

    try:
        if user.role == 'teacher':
            has = course in user.teaching_courses
            if desired_assigned and not has:
                user.teaching_courses.append(course)
            elif not desired_assigned and has:
                user.teaching_courses.remove(course)
        elif user.role == 'student':
            has = course in user.enrolled_courses
            if desired_assigned and not has:
                user.enrolled_courses.append(course)
            elif not desired_assigned and has:
                user.enrolled_courses.remove(course)
        else:
            return {'error': 'Некорректная роль пользователя'}, 400

        db.session.commit()
        return {'ok': True, 'assigned': desired_assigned}
    except Exception as e:
        db.session.rollback()
        return {'error': f'Ошибка обновления: {str(e)}'}, 500

@app.route('/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role != 'teacher':
        flash('У вас нет прав отмечать посещаемость.', 'danger')
        return redirect(url_for('index'))

    form = MarkAttendanceForm()

    # Получаем курсы преподавателя через relationship
    teacher_courses = current_user.teaching_courses
    
    # Если у преподавателя нет курсов, показываем сообщение
    if not teacher_courses:
        flash('Вы не назначены ни на один курс.', 'warning')
    
    form.course_id.choices = [(c.id, c.name) for c in teacher_courses]

    # Обработка выбора курса
    selected_course_id = request.args.get('course_id', type=int) or \
                       (form.course_id.data if request.method == 'POST' else None)

    if selected_course_id:
        selected_course = next((c for c in teacher_courses if c.id == selected_course_id), None)
        
        if selected_course:
            # Более надежная загрузка студентов
            db.session.refresh(selected_course)
            
            # Сначала пробуем через relationship
            if hasattr(selected_course, 'students') and selected_course.students:
                form.student_id.choices = [(s.id, s.username) for s in selected_course.students]
            else:
                # Если relationship не работает, загружаем через прямую связь
                from app.models import User
                enrolled_students = db.session.query(User).join(User.enrolled_courses).filter(
                    Course.id == selected_course.id
                ).all()
                form.student_id.choices = [(s.id, s.username) for s in enrolled_students]
            
            # Если на курсе нет студентов
            if not form.student_id.choices:
                flash(f'На курс {selected_course.name} не записаны студенты', 'info')
        else:
            form.student_id.choices = []
            flash('Курс не найден или доступ запрещён', 'danger')
    else:
        form.student_id.choices = []

    if form.validate_on_submit():
        student = db.session.get(User, form.student_id.data)
        course = db.session.get(Course, form.course_id.data)

        if not student or not course:
            flash('Выбран некорректный студент или курс.', 'danger')
            return redirect(url_for('mark_attendance'))
        
        if student.role != 'student':
            flash('Только для студентов возможны записи посещаемости.', 'danger')
            return redirect(url_for('mark_attendance'))

        # Проверяем, что студент записан на курс (более надежная проверка)
        # Сначала обновляем курс, чтобы убедиться, что связи загружены
        db.session.refresh(course)
        
        # Проверяем через relationship
        is_enrolled = student in course.students
        
        # Если relationship не работает, проверяем через прямую связь
        if not is_enrolled:
            # Проверяем через таблицу связей
            direct_check = db.session.query(User).join(User.enrolled_courses).filter(
                User.id == student.id,
                Course.id == course.id
            ).first()
            is_enrolled = direct_check is not None
        
        if not is_enrolled:
            flash(f'Студент {student.username} не записан на курс {course.name}.', 'danger')
            return redirect(url_for('mark_attendance'))

        # Проверяем, что учитель преподает этот курс
        if course not in current_user.teaching_courses:
            flash(f'У вас нет прав отмечать посещаемость по курсу {course.name}.', 'danger')
            return redirect(url_for('mark_attendance'))

        # Создаем запись о посещаемости
        attendance = AttendanceRecord(
            student_id=student.id,
            course_id=course.id,
            status=form.status.data,
            notes=form.notes.data
        )
        db.session.add(attendance)
        db.session.commit()
        
        flash(f'Посещаемость отмечена для {student.username} по курсу {course.name}.', 'success')
        return redirect(url_for('mark_attendance'))
    
    return render_template('mark_attendance.html', title='Отметить посещаемость', form=form)

@app.route('/api/get_students_for_course')
@login_required
def get_students_for_course():
    if current_user.role != 'teacher':
        return {'error': 'Доступ запрещен'}, 403
    
    course_id = request.args.get('course_id', type=int)
    if not course_id:
        return {'error': 'ID курса не указан'}, 400
    
    course = db.session.get(Course, course_id)
    if not course:
        return {'error': 'Курс не найден'}, 404
    
    # Проверяем, что преподаватель преподает этот курс
    if course not in current_user.teaching_courses:
        return {'error': 'У вас нет прав на этот курс'}, 403
    
    # Получаем студентов курса (более надежная загрузка)
    # Сначала обновляем курс, чтобы убедиться, что связи загружены
    db.session.refresh(course)
    
    students = []
    # Проверяем, загружены ли студенты
    if hasattr(course, 'students') and course.students:
        for student in course.students:
            students.append({
                'id': student.id,
                'username': student.username
            })
    else:
        # Если relationship не работает, загружаем через прямую связь
        enrolled_students = db.session.query(User).join(User.enrolled_courses).filter(
            Course.id == course.id
        ).all()
        for student in enrolled_students:
            students.append({
                'id': student.id,
                'username': student.username
            })
    
    return {'students': students}

@app.route('/chat_list')
@login_required
def chat_list():
    page = request.args.get('page', 1, type=int)
    # Получаем список пользователей для чата
    users_query = sa.select(User).where(User.id != current_user.id).order_by(User.username)
    users_pagination = db.paginate(
        users_query,
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    users = users_pagination.items
    next_url = url_for('chat_list', page=users_pagination.next_num) \
        if users_pagination.has_next else None
    prev_url = url_for('chat_list', page=users_pagination.prev_num) \
        if users_pagination.has_prev else None
    
    return render_template('chat_list.html', 
                         title='Список чатов',
                         users=users,
                         next_url=next_url,
                         prev_url=prev_url)

@app.route('/chat/<username>', methods=['GET', 'POST'])
@login_required
def chat(username):
    other_user = db.first_or_404(sa.select(User).where(User.username == username))
    if other_user == current_user:
        flash('Вы не можете написать сообщение самому себе.', 'warning')
        return redirect(url_for('chat_list'))
    
    page = request.args.get('page', 1, type=int)
    # Получаем сообщения между текущим пользователем и выбранным
    messages_query = sa.select(Message).where(
        sa.or_(
            sa.and_(Message.sender_id == current_user.id, Message.recipient_id == other_user.id),
            sa.and_(Message.sender_id == other_user.id, Message.recipient_id == current_user.id)
        )
    ).order_by(Message.timestamp.desc())
    
    messages_pagination = db.paginate(
        messages_query,
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    messages = messages_pagination.items
    next_url = url_for('chat', username=username, page=messages_pagination.next_num) \
        if messages_pagination.has_next else None
    prev_url = url_for('chat', username=username, page=messages_pagination.prev_num) \
        if messages_pagination.has_prev else None
    
    form = MessageForm()
    if form.validate_on_submit():
        message = Message(
            sender_id=current_user.id,
            recipient_id=other_user.id,
            body=form.message.data
        )
        db.session.add(message)
        db.session.commit()
        return redirect(url_for('chat', username=username))
    
    return render_template('chat.html', 
                         title=f'Чат с {username}',
                         messages=messages,
                         form=form,
                         other_user=other_user,
                         next_url=next_url,
                         prev_url=prev_url)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash('Проверьте вашу электронную почту для получения инструкций по сбросу пароля.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title='Сброс пароля', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Ваш пароль был изменен.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', title='Сброс пароля', form=form)

@app.route('/toggle_favorite/<int:course_id>')
@login_required
def toggle_favorite(course_id):
    course = db.get_or_404(Course, course_id)
    course.is_favorite = not course.is_favorite
    db.session.commit()
    
    if course.is_favorite:
        flash(f'Курс "{course.name}" добавлен в избранное', 'success')
        # После добавления в избранное перенаправляем с сортировкой "избранные первыми"
        return redirect(url_for('courses', sort_by='favorites_first'))
    else:
        flash(f'Курс "{course.name}" удален из избранного', 'info')
        # После удаления из избранного возвращаемся к сортировке "избранные первыми"
        return redirect(url_for('courses', sort_by='favorites_first'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    """Удаление пользователя (только для админов)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    user = User.query.get_or_404(user_id)
    username = user.username  # Сохраняем имя для сообщения
    
    # Нельзя удалить самого себя
    if user.id == current_user.id:
        flash('Нельзя удалить свой собственный аккаунт', 'danger')
        return redirect(url_for('admin_panel'))
    
    try:
        # Удаляем связанные записи в правильном порядке
        AttendanceRecord.query.filter_by(student_id=user.id).delete()
        Message.query.filter_by(sender_id=user.id).delete()
        Message.query.filter_by(recipient_id=user.id).delete()
        News.query.filter_by(author_id=user.id).delete()
        
        # Удаляем связи many-to-many
        user.teaching_courses.clear()
        user.enrolled_courses.clear()
        
        # Удаляем пользователя
        db.session.delete(user)
        db.session.commit()
        
        flash(f'Пользователь {username} успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
def admin_delete_course(course_id):
    """Удаление курса (только для админов)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    course = Course.query.get_or_404(course_id)
    course_name = course.name  # Сохраняем имя для сообщения
    
    try:
        # Удаляем связанные записи посещаемости
        AttendanceRecord.query.filter_by(course_id=course.id).delete()
        
        # Удаляем связи many-to-many
        course.teachers.clear()
        course.students.clear()
        
        # Удаляем курс
        db.session.delete(course)
        db.session.commit()
        
        flash(f'Курс "{course_name}" успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении курса: {str(e)}', 'danger')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_news/<int:news_id>', methods=['POST'])
@login_required
def admin_delete_news(news_id):
    """Удаление новости (только для админов)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    news = News.query.get_or_404(news_id)
    news_title = news.title  # Сохраняем заголовок для сообщения
    
    try:
        # Удаляем новость
        db.session.delete(news)
        db.session.commit()
        
        flash(f'Новость "{news_title}" успешно удалена', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении новости: {str(e)}', 'danger')
    
    return redirect(url_for('admin_panel'))
