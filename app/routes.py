from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, CourseForm, MarkAttendanceForm, AssignCourseForm, MessageForm, ResetPasswordForm, NewsForm, ResetPasswordRequestForm, CreateGroupForm, RoomForm
from app.models import User, Course, AttendanceRecord, Message, News, Group, Schedule, Room, TeacherSubstitution
from datetime import datetime, timezone, timedelta
import sqlalchemy as sa
import sqlalchemy.orm as so
from urllib.parse import urlsplit
from app.email import send_password_reset_email

def get_user_courses(user, role_type='all'):
    if user.role == 'student':
        return user.enrolled_courses if role_type in ['all', 'enrolled'] else []
    elif user.role == 'teacher':
        return user.teaching_courses if role_type in ['all', 'teaching'] else []
    else:
        return Course.query.all() if role_type in ['all'] else []

def get_stats():
    return {
        'total_users': User.query.count(),
        'total_students': User.query.filter_by(role='student').count(),
        'total_teachers': User.query.filter_by(role='teacher').count(),
        'total_admins': User.query.filter_by(role='admin').count(),
        'total_courses': Course.query.count(),
        'active_courses': Course.query.count(),  # Можно добавить условие для активных курсов
        'total_enrollments': sum(len(course.students) for course in Course.query.all()),
        'total_teachers_assigned': len(set(teacher.id for course in Course.query.all() for teacher in course.teachers))
    }

def get_recent_news(limit=5):
    return db.session.query(News).order_by(News.created_at.desc()).limit(limit).all()

def get_group_data(user):
    if user.role == 'student':
        enrolled_courses = user.enrolled_courses
        students = set()
        
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
        teaching_courses = user.teaching_courses
        students = set()
        
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
    
    recent_news = get_recent_news()
    
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
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    stats = get_stats()
    
    users = User.query.filter(User.id != current_user.id).order_by(User.role, User.username).all()
    
    courses = Course.query.all()
    
    recent_news = get_recent_news(6)
    
    from datetime import datetime
    return render_template('admin/admin_panel.html',
                         stats=stats,
                         users=users,
                         courses=courses,
                         news_list=recent_news,
                         moment=datetime.now())

@app.route('/admin/users')
@login_required
def admin_users():
    """Страница управления пользователями"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    stats = get_stats()
    users = User.query.filter(User.id != current_user.id).order_by(User.role, User.username).all()
    
    return render_template('admin/admin_users.html',
                         title='Управление пользователями',
                         stats=stats,
                         users=users)

@app.route('/admin/courses')
@login_required
def admin_courses():
    """Страница управления курсами"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))
    
    stats = get_stats()
    courses = Course.query.all()
    all_teachers = User.query.filter_by(role='teacher').all()
    
    return render_template('admin/admin_courses.html',
                         title='Управление курсами',
                         stats=stats,
                         courses=courses,
                         all_teachers=all_teachers)

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
    
    return render_template('admin/create_news.html', title='Создать новость', form=form)

@app.route('/calendar')
@login_required
def calendar():
    
    current_date = datetime.now()
    
    year = request.args.get('year', current_date.year, type=int)
    month = request.args.get('month', current_date.month, type=int)
    
    if month < 1 or month > 12:
        month = 1
    if year < 1900 or year > 2100:
        year = current_date.year
    
    user_courses = get_user_courses(current_user)
    schedule_data = {
        'courses': user_courses,
        'role': current_user.role
    }
    
    # Определяем выбранную дату (по умолчанию сегодня)
    selected_date = current_date
    
    return render_template('calendar.html',
                         title='Календарь',
                         year=year,
                         month=month,
                         current_date=current_date,
                         selected_date=selected_date,
                         schedule_data=schedule_data,
                         datetime=datetime,
                         timedelta=timedelta)

@app.route('/group')
@login_required
def group():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    groups_query = sa.select(Group)
    
    if search:
        groups_query = groups_query.where(
            sa.or_(
                Group.name.ilike(f'%{search}%'),
                Group.specialty.ilike(f'%{search}%')
            )
        )
    
    groups_query = groups_query.order_by(Group.name)
    
    groups = db.session.execute(groups_query).scalars().unique().all()
    
    per_page = 16
    total_groups = len(groups)
    total_pages = (total_groups + per_page - 1) // per_page
    
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    groups_page = groups[start_idx:end_idx]
    
    next_url = url_for('group', page=page + 1, search=search) \
        if page < total_pages else None
    prev_url = url_for('group', page=page - 1, search=search) \
        if page > 1 else None
    
    return render_template('groups/group.html',
                         title='Группы',
                         groups=groups_page,
                         next_url=next_url,
                         prev_url=prev_url,
                         search=search)

@app.route('/group/<int:group_id>')
@login_required
def view_group(group_id):
    group = db.get_or_404(Group, group_id)
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    except ValueError:
        selected_date_obj = datetime.now()
        selected_date = selected_date_obj.strftime('%Y-%m-%d')
    
    students = group.students
    
    attendance_stats = {}
    for student in students:
        student_records = db.session.query(AttendanceRecord).filter(
            AttendanceRecord.student_id == student.id,
            sa.func.date(AttendanceRecord.date) == selected_date_obj.date()
        ).all()
        
        if not student_records:
            attendance_stats[student.id] = {
                'status': 'not_marked',
                'notes': '',
                'course_name': 'Не отмечено'
            }
        else:
            record = student_records[0]
            attendance_stats[student.id] = {
                'status': record.status,
                'notes': record.notes or '',
                'course_name': record.course.name if record.course else 'Неизвестный курс'
            }
    
    # Определяем текущий месяц для календаря
    current_month = selected_date_obj.replace(day=1)
    today = datetime.now().date()
    
    # Подсчитываем статистику посещаемости
    present_count = sum(1 for stats in attendance_stats.values() if stats['status'] == 'present')
    absent_count = sum(1 for stats in attendance_stats.values() if stats['status'] == 'absent')
    late_count = sum(1 for stats in attendance_stats.values() if stats['status'] == 'late')
    
    return render_template('groups/view_group.html',
                         title=f'Группа {group.name}',
                         group=group,
                         students=students,
                         attendance_stats=attendance_stats,
                         selected_date=selected_date,
                         selected_date_obj=selected_date_obj,
                         current_month=current_month,
                         today=today,
                         present_count=present_count,
                         absent_count=absent_count,
                         late_count=late_count,
                         datetime=datetime,
                         timedelta=timedelta)

@app.route('/group/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    if not current_user.is_admin():
        flash('У вас нет прав для редактирования групп.', 'error')
        return redirect(url_for('group'))
    
    group = db.get_or_404(Group, group_id)
    
    if request.method == 'POST':
        group.name = request.form.get('name', group.name)
        group.specialty = request.form.get('specialty', group.specialty)
        group.course_year = int(request.form.get('course_year', group.course_year))
        group.group_number = int(request.form.get('group_number', group.group_number))
        group.max_students = int(request.form.get('max_students', group.max_students))
        
        try:
            db.session.commit()
            flash(f'Группа {group.name} успешно обновлена!', 'success')
            return redirect(url_for('view_group', group_id=group.id))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при обновлении группы.', 'error')
    
    return render_template('groups/edit_group.html', group=group)

@app.route('/group/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    if not current_user.is_admin():
        flash('У вас нет прав для удаления групп.', 'error')
        return redirect(url_for('group'))
    
    group = db.get_or_404(Group, group_id)
    group_name = group.name
    
    try:
        # Удаляем все связи студентов с группой
        for student in group.students:
            student.group = None
        
        db.session.delete(group)
        db.session.commit()
        flash(f'Группа {group_name} успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении группы.', 'error')
    
    return redirect(url_for('group'))

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
    return render_template('auth/login.html', title='Вход', form=form)

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
    return render_template('auth/register.html', title='Регистрация', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    
    if user.role == 'student':

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
    if current_user.role not in ['teacher', 'admin']:
        flash('У вас нет прав создавать курсы.', 'danger')
        return redirect(url_for('index'))
    
    form = CourseForm()
    if form.validate_on_submit():
        try:
            course = Course(name=form.name.data, description=form.description.data)

            course.teachers.append(current_user)
            db.session.add(course)
            db.session.commit()
            flash('Курс создан успешно!', 'success')
            return redirect(url_for('courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка создания курса: {str(e)}', 'danger')
    
    return render_template('courses/create_edit_course.html', title='Создать курс', form=form)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = db.get_or_404(Course, course_id)
    

    if current_user.is_admin():
        pass

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
    
    return render_template('courses/create_edit_course.html', title='Редактировать курс', form=form, course=course)

@app.route('/courses')
@login_required
def courses():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'favorites_first')
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
    
    # Применяем фильтр по избранным (для текущего пользователя)
    if filter_favorites == 'favorites':

        favorite_course_ids = [c.id for c in current_user.favorite_courses]
        if favorite_course_ids:
            courses_query = courses_query.where(Course.id.in_(favorite_course_ids))
        else:
            courses_query = courses_query.where(Course.id == 0)
    elif filter_favorites == 'not_favorites':
        favorite_course_ids = [c.id for c in current_user.favorite_courses]
        if favorite_course_ids:
            courses_query = courses_query.where(Course.id.notin_(favorite_course_ids))
    
    if sort_by == 'name':
        courses_query = courses_query.order_by(Course.name)
    elif sort_by == 'name_desc':
        courses_query = courses_query.order_by(Course.name.desc())
    elif sort_by == 'favorites_first':
        pass
    elif sort_by == 'description':
        courses_query = courses_query.order_by(Course.description)
    else:
        pass
    
    courses = db.session.execute(courses_query).scalars().unique().all()
    
    if sort_by == 'favorites_first':
        favorite_course_ids = {c.id for c in current_user.favorite_courses}
        
        courses.sort(key=lambda c: (not favorite_course_ids.__contains__(c.id), c.name.lower()))
    
    per_page = 16
    total_courses = len(courses)
    total_pages = (total_courses + per_page - 1) // per_page
    
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    courses_page = courses[start_idx:end_idx]
    
    next_url = url_for('courses', page=page + 1, search=search, sort_by=sort_by, filter_favorites=filter_favorites) \
        if page < total_pages else None
    prev_url = url_for('courses', page=page - 1, search=search, sort_by=sort_by, filter_favorites=filter_favorites) \
        if page > 1 else None
    
    courses = courses_page
    
    return render_template('courses/courses.html', 
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
    
    if not current_user.is_admin():
        flash('Только администраторы могут удалять курсы.', 'danger')
        return redirect(url_for('courses'))
    
    try:
        AttendanceRecord.query.filter_by(course_id=course.id).delete()
        
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
    if not current_user.is_admin():
        flash('Только администраторы могут назначать пользователей на курсы.', 'danger')
        return redirect(url_for('index'))

    form = AssignCourseForm()
    
    # Устанавливаем пустые choices для формы (поиск будет через API)
    form.user_id.choices = []
    form.course_id.choices = []

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
    
    return render_template('courses/assign_to_course.html', title='Назначить на курс', form=form)

@app.route('/api/user_courses_status')
@login_required
def api_user_courses_status():
    # Доступ только администраторам
    if not current_user.is_admin():
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
    # Доступ только преподавателям и администраторам
    if current_user.role not in ['teacher', 'admin']:
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
    # Доступ только преподавателям и администраторам
    if current_user.role not in ['teacher', 'admin']:
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

@app.route('/api/search_users')
@login_required
def api_search_users():
    # Доступ только администраторам
    if not current_user.is_admin():
        return {'error': 'Доступ запрещен'}, 403

    query = request.args.get('q', '').strip()
    if len(query) < 1:
        return {'users': []}

    # Поиск пользователей по имени (регистронезависимый)
    users = db.session.query(User).filter(
        User.username.ilike(f'%{query}%')
    ).order_by(User.username).limit(10).all()

    return {
        'users': [
            {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
            for user in users
        ]
    }

@app.route('/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role not in ['teacher', 'admin']:
        flash('У вас нет прав отмечать посещаемость.', 'danger')
        return redirect(url_for('index'))

    form = MarkAttendanceForm()

    # Получаем курсы в зависимости от роли
    if current_user.role == 'admin':
        # Администраторы видят все курсы
        available_courses = Course.query.all()
    else:
        # Преподаватели видят только свои курсы
        available_courses = current_user.teaching_courses
    
    # Если нет доступных курсов, показываем сообщение
    if not available_courses:
        if current_user.role == 'admin':
            flash('В системе нет курсов.', 'warning')
        else:
            flash('Вы не назначены ни на один курс.', 'warning')
    
    form.course_id.choices = [(c.id, c.name) for c in available_courses]

    # Обработка выбора курса
    selected_course_id = request.args.get('course_id', type=int) or \
                       (form.course_id.data if request.method == 'POST' else None)

    if selected_course_id:
        selected_course = next((c for c in available_courses if c.id == selected_course_id), None)
        
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
    if current_user.role not in ['teacher', 'admin']:
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
    
    return render_template('chat/chat_list.html', 
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
    
    return render_template('chat/chat.html', 
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
    return render_template('auth/reset_password_request.html', title='Сброс пароля', form=form)

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
    return render_template('auth/reset_password.html', title='Сброс пароля', form=form)

@app.route('/toggle_favorite/<int:course_id>')
@login_required
def toggle_favorite(course_id):
    course = db.get_or_404(Course, course_id)
    
    # Проверяем, является ли курс избранным для текущего пользователя
    is_favorite = current_user.is_course_favorite(course)
    
    if is_favorite:
        # Убираем из избранного
        current_user.remove_favorite_course(course)
        flash(f'Курс "{course.name}" удален из избранного', 'info')
    else:
        # Добавляем в избранное
        current_user.add_favorite_course(course)
        flash(f'Курс "{course.name}" добавлен в избранное', 'success')
    
    db.session.commit()
    
    # После изменения избранного перенаправляем с сортировкой "избранные первыми"
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

@app.route('/admin/create_groups', methods=['GET', 'POST'])
@login_required
def admin_create_groups():
    """Создание групп (только для админов)"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    form = CreateGroupForm()
    
    if form.validate_on_submit():
        try:
            # Создаем новую группу
            group = Group(
                name=form.name.data,
                specialty=form.specialty.data,
                course_year=form.course_year.data,
                group_number=form.group_number.data,
                max_students=form.max_students.data
            )
            
            db.session.add(group)
            db.session.commit()
            
            flash(f'Группа "{group.name}" создана успешно!', 'success')
            return redirect(url_for('admin_create_groups'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании группы: {str(e)}', 'danger')
    
    # Получаем существующие группы для отображения
    existing_groups = Group.query.order_by(Group.course_year, Group.specialty, Group.group_number).all()
    
    return render_template('admin/admin_create_groups.html', 
                         title='Создать группы', 
                         form=form, 
                         existing_groups=existing_groups)

@app.route('/schedule')
@login_required
def schedule():
    """Страница расписания для всех пользователей"""
    # Получаем параметр недели из URL
    week_offset = request.args.get('week', 0, type=int)
    
    # Получаем текущую неделю с учетом смещения
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    
    # Получаем расписание в зависимости от роли пользователя
    if current_user.role == 'student':
        # Для студентов показываем расписание их группы
        if hasattr(current_user, 'group') and current_user.group:
            schedules = Schedule.query.filter_by(
                group_id=current_user.group.id,
                is_active=True
            ).order_by(Schedule.day_of_week, Schedule.slot_number).all()
        else:
            schedules = []
        view_type = 'student'
    elif current_user.role == 'teacher':
        # Для преподавателей показываем их расписание
        schedules = Schedule.query.filter_by(
            teacher_id=current_user.id,
            is_active=True
        ).order_by(Schedule.day_of_week, Schedule.slot_number).all()
        view_type = 'teacher'
    else:
        # Для администраторов показываем все расписание
        schedules = Schedule.query.filter_by(is_active=True).order_by(
            Schedule.group_id, Schedule.day_of_week, Schedule.slot_number
        ).all()
        view_type = 'admin'
    
    # Группируем расписание по дням недели
    week_schedule = {}
    for day in range(1, 8):  # Понедельник-Воскресенье
        week_schedule[day] = {}
        for slot in range(1, 5):  # 1-4 пары
            week_schedule[day][slot] = []
    
    # Заполняем расписание
    for schedule in schedules:
        if schedule.day_of_week in week_schedule and schedule.slot_number in week_schedule[schedule.day_of_week]:
            week_schedule[schedule.day_of_week][schedule.slot_number].append(schedule)
    
    # Названия дней недели
    days_names = {
        1: 'Понедельник',
        2: 'Вторник', 
        3: 'Среда',
        4: 'Четверг',
        5: 'Пятница',
        6: 'Суббота',
        7: 'Воскресенье'
    }
    
    # Сокращения дней недели
    days_short = {
        1: 'Пн',
        2: 'Вт', 
        3: 'Ср',
        4: 'Чт',
        5: 'Пт',
        6: 'Сб',
        7: 'Вс'
    }
    
    # Время пар
    slots_time = {
        1: '8:30 - 10:00',
        2: '10:10 - 11:40',
        3: '12:10 - 13:40',
        4: '14:10 - 15:40'
    }
    
    # Определяем выбранный день (по умолчанию текущий день недели)
    current_weekday = today.weekday() + 1  # Понедельник = 1, Воскресенье = 7
    if week_offset == 0:  # Только для текущей недели
        selected_day = current_weekday
    else:
        selected_day = 1  # Для других недель показываем понедельник
    
    # Вычисляем даты для каждого дня недели
    week_dates = {}
    for day_num in range(1, 8):  # Понедельник-Воскресенье
        week_dates[day_num] = (start_of_week + timedelta(days=day_num-1)).strftime('%d.%m')
    
    # Вычисляем диапазон недели для отображения
    week_range = f"{start_of_week.strftime('%d.%m')} - {(start_of_week + timedelta(days=6)).strftime('%d.%m.%Y')}"
    
    # Получаем список специальностей для фильтра
    specialties = []
    courses_by_specialty = {}
    groups_by_specialty = {}
    
    if view_type == 'admin':
        # Для администраторов показываем все специальности из базы данных
        specialties = db.session.query(Group.specialty).distinct().order_by(Group.specialty).all()
        specialties = [s[0] for s in specialties]
    else:
        # Для студентов и преподавателей показываем только их специальности
        if view_type == 'student' and hasattr(current_user, 'group') and current_user.group:
            specialties = [current_user.group.specialty]
        elif view_type == 'teacher':
            # Получаем специальности групп, которые преподает учитель
            teacher_specialties = set()
            for schedule in schedules:
                if schedule.group and schedule.group.specialty:
                    teacher_specialties.add(schedule.group.specialty)
            specialties = list(teacher_specialties)
    
    # Группируем курсы и группы по специальностям
    for schedule in schedules:
        if schedule.group and schedule.group.specialty:
            specialty = schedule.group.specialty
            course_year = schedule.group.course_year
            group_number = schedule.group.group_number
            
            if specialty not in courses_by_specialty:
                courses_by_specialty[specialty] = set()
                groups_by_specialty[specialty] = {}
            
            courses_by_specialty[specialty].add(course_year)
            
            if course_year not in groups_by_specialty[specialty]:
                groups_by_specialty[specialty][course_year] = set()
            groups_by_specialty[specialty][course_year].add(group_number)
    
    # Преобразуем в списки для шаблона
    for specialty in courses_by_specialty:
        courses_by_specialty[specialty] = sorted(list(courses_by_specialty[specialty]))
        for course_year in groups_by_specialty[specialty]:
            groups_by_specialty[specialty][course_year] = sorted(list(groups_by_specialty[specialty][course_year]))
    
    return render_template('schedule.html',
                         title='Расписание',
                         week_schedule=week_schedule,
                         days_names=days_names,
                         days_short=days_short,
                         slots_time=slots_time,
                         view_type=view_type,
                         start_of_week=start_of_week,
                         selected_day=selected_day,
                         week_dates=week_dates,
                         week_offset=week_offset,
                         current_weekday=current_weekday,
                         week_range=week_range,
                         specialties=specialties,
                         courses_by_specialty=courses_by_specialty,
                         groups_by_specialty=groups_by_specialty)

@app.route('/admin/schedule')
@login_required
def admin_schedule():
    """Административная панель для управления расписанием"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    # Получаем все группы, курсы, преподавателей и аудитории
    groups = Group.query.all()
    courses = Course.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    rooms = Room.query.all()
    
    # Получаем текущее расписание
    schedules = Schedule.query.filter_by(is_active=True).order_by(
        Schedule.group_id, Schedule.day_of_week, Schedule.slot_number
    ).all()
    
    # Группируем расписание по группам
    group_schedules = {}
    schedules_dict = {}
    
    for group in groups:
        group_schedules[group.id] = {}
        for day in range(1, 6):
            group_schedules[group.id][day] = {}
            for slot in range(1, 5):
                group_schedules[group.id][day][slot] = None
    
    # Заполняем расписание
    for schedule in schedules:
        if (schedule.group_id in group_schedules and 
            schedule.day_of_week in group_schedules[schedule.group_id] and
            schedule.slot_number in group_schedules[schedule.group_id][schedule.day_of_week]):
            group_schedules[schedule.group_id][schedule.day_of_week][schedule.slot_number] = schedule
            # Создаем словарь для шаблона
            schedules_dict[(schedule.group_id, schedule.day_of_week, schedule.slot_number)] = schedule
    
    return render_template('admin/admin_schedule.html',
                         title='Управление расписанием',
                         groups=groups,
                         courses=courses,
                         teachers=teachers,
                         rooms=rooms,
                         group_schedules=group_schedules,
                         schedules=schedules_dict)

@app.route('/admin/schedule/edit', methods=['POST'])
@login_required
def admin_schedule_edit():
    """Редактирование расписания"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    data = request.get_json()
    
    try:
        schedule_id = data.get('schedule_id')
        group_id = data.get('group_id')
        course_id = data.get('course_id')
        teacher_id = data.get('teacher_id')
        room_id = data.get('room_id')
        day_of_week = data.get('day_of_week')
        slot_number = data.get('slot_number')
        
        if schedule_id:
            # Редактируем существующее расписание
            schedule = Schedule.query.get_or_404(schedule_id)
            schedule.course_id = course_id
            schedule.teacher_id = teacher_id
            schedule.room_id = room_id
        else:
            # Создаем новое расписание
            schedule = Schedule(
                group_id=group_id,
                course_id=course_id,
                teacher_id=teacher_id,
                room_id=room_id,
                day_of_week=day_of_week,
                slot_number=slot_number
            )
            db.session.add(schedule)
        
        db.session.commit()
        
        return {'success': True, 'message': 'Расписание обновлено'}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Ошибка: {str(e)}'}

@app.route('/admin/schedule/delete', methods=['POST'])
@login_required
def admin_schedule_delete():
    """Удаление записи из расписания"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    data = request.get_json()
    schedule_id = data.get('schedule_id')
    
    try:
        schedule = Schedule.query.get_or_404(schedule_id)
        db.session.delete(schedule)
        db.session.commit()
        
        return {'success': True, 'message': 'Запись удалена'}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Ошибка: {str(e)}'}

@app.route('/admin/substitutions')
@login_required
def admin_substitutions():
    """Управление заменами преподавателей"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    substitutions = TeacherSubstitution.query.order_by(TeacherSubstitution.date.desc()).all()
    
    return render_template('admin/admin_substitutions.html',
                         title='Замены преподавателей',
                         substitutions=substitutions)

@app.route('/admin/substitution/create', methods=['POST'])
@login_required
def admin_substitution_create():
    """Создание замены преподавателя"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    data = request.get_json()
    
    try:
        substitution = TeacherSubstitution(
            original_schedule_id=data['schedule_id'],
            substitute_teacher_id=data['teacher_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            reason=data.get('reason', '')
        )
        
        db.session.add(substitution)
        db.session.commit()
        
        return {'success': True, 'message': 'Замена создана'}
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Ошибка: {str(e)}'}

@app.route('/admin/rooms')
@login_required
def admin_rooms():
    """Управление аудиториями"""
    if not current_user.is_admin():
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('admin_panel'))
    
    rooms = Room.query.all()
    
    return render_template('admin/admin_rooms.html',
                         title='Управление аудиториями',
                         rooms=rooms)

@app.route('/admin/rooms/create', methods=['POST'])
@login_required
def admin_room_create():
    """Создание новой аудитории"""
    if not current_user.is_admin():
        return {'success': False, 'message': 'Доступ запрещен'}, 403
    
    try:
        data = request.get_json()
        
        # Логируем полученные данные для отладки
        print(f"Создание новой аудитории:")
        print(f"Полученные данные: {data}")
        
        # Проверяем наличие обязательных полей
        required_fields = ['number', 'building', 'room_type', 'capacity']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            return {'success': False, 'message': f'Отсутствуют обязательные поля: {", ".join(missing_fields)}'}, 400
        
        # Проверяем валидность данных
        if not isinstance(data['capacity'], (int, str)) or int(data['capacity']) < 1 or int(data['capacity']) > 500:
            return {'success': False, 'message': 'Вместимость должна быть от 1 до 500 мест'}, 400
            
        if len(data['number'].strip()) == 0 or len(data['number']) > 20:
            return {'success': False, 'message': 'Номер аудитории должен быть от 1 до 20 символов'}, 400
            
        if len(data['building'].strip()) == 0 or len(data['building']) > 50:
            return {'success': False, 'message': 'Название корпуса должно быть от 1 до 50 символов'}, 400
        
        # Проверяем, существует ли аудитория с таким номером
        existing_room = Room.query.filter_by(number=data['number'].strip()).first()
        if existing_room:
            return {'success': False, 'message': f'Аудитория {data["number"]} уже существует'}, 400
        
        # Создаем новую аудиторию
        room = Room(
            number=data['number'].strip(),
            building=data['building'].strip(),
            room_type=data['room_type'],
            capacity=int(data['capacity']),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(room)
        db.session.commit()
        
        print(f"Аудитория успешно создана: {room.number}")
        
        return {
            'success': True, 
            'message': f'Аудитория {room.number} создана успешно',
            'room': {
                'id': room.id,
                'number': room.number,
                'building': room.building,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'is_active': room.is_active
            }
        }
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при создании аудитории: {str(e)}")
        return {'success': False, 'message': f'Ошибка создания аудитории: {str(e)}'}, 500

@app.route('/admin/rooms/<int:room_id>/update', methods=['POST'])
@login_required
def admin_room_update(room_id):
    """Обновление аудитории"""
    if not current_user.is_admin():
        return {'success': False, 'message': 'Доступ запрещен'}, 403
    
    try:
        room = Room.query.get_or_404(room_id)
        data = request.get_json()
        
        # Логируем полученные данные для отладки
        print(f"Обновление аудитории {room_id}:")
        print(f"Полученные данные: {data}")
        print(f"Текущая аудитория: номер={room.number}, корпус={room.building}")
        
        # Проверяем наличие обязательных полей
        required_fields = ['number', 'building', 'room_type', 'capacity']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            return {'success': False, 'message': f'Отсутствуют обязательные поля: {", ".join(missing_fields)}'}, 400
        
        # Проверяем валидность данных
        if not isinstance(data['capacity'], (int, str)) or int(data['capacity']) < 1 or int(data['capacity']) > 500:
            return {'success': False, 'message': 'Вместимость должна быть от 1 до 500 мест'}, 400
            
        if len(data['number'].strip()) == 0 or len(data['number']) > 20:
            return {'success': False, 'message': 'Номер аудитории должен быть от 1 до 20 символов'}, 400
            
        if len(data['building'].strip()) == 0 or len(data['building']) > 50:
            return {'success': False, 'message': 'Название корпуса должно быть от 1 до 50 символов'}, 400
        
        # Проверяем, не занят ли новый номер другой аудиторией
        if data['number'].strip() != room.number:
            existing_room = Room.query.filter_by(number=data['number'].strip()).first()
            if existing_room:
                return {'success': False, 'message': f'Аудитория {data["number"]} уже существует'}, 400
        
        # Обновляем данные аудитории
        room.number = data['number'].strip()
        room.building = data['building'].strip()
        room.room_type = data['room_type']
        room.capacity = int(data['capacity'])
        room.is_active = data.get('is_active', True)
        
        db.session.commit()
        
        print(f"Аудитория успешно обновлена: {room.number}")
        
        return {
            'success': True, 
            'message': f'Аудитория {room.number} обновлена успешно',
            'room': {
                'id': room.id,
                'number': room.number,
                'building': room.building,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'is_active': room.is_active
            }
        }
        
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при обновлении аудитории: {str(e)}")
        return {'success': False, 'message': f'Ошибка обновления аудитории: {str(e)}'}, 500

@app.route('/admin/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
def admin_room_delete(room_id):
    """Удаление аудитории"""
    if not current_user.is_admin():
        return {'success': False, 'message': 'Доступ запрещен'}, 403
    
    try:
        room = Room.query.get_or_404(room_id)
        room_number = room.number
        
        # Проверяем, используется ли аудитория в расписании
        schedules_using_room = Schedule.query.filter_by(room_id=room.id, is_active=True).count()
        if schedules_using_room > 0:
            return {
                'success': False, 
                'message': f'Аудитория {room_number} используется в расписании ({schedules_using_room} занятий). Сначала удалите или измените расписание.'
            }, 400
        
        db.session.delete(room)
        db.session.commit()
        
        return {
            'success': True, 
            'message': f'Аудитория {room_number} удалена успешно'
        }
        
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'message': f'Ошибка удаления аудитории: {str(e)}'}, 500
