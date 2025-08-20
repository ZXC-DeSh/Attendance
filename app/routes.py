from flask import render_template, flash, redirect, url_for, request, current_app
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, CourseForm, MarkAttendanceForm, AssignCourseForm, MessageForm, ResetPasswordRequestForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.models import User, Course, AttendanceRecord, Message
from urllib.parse import urlsplit
from datetime import datetime, timezone
 
from app.email import send_password_reset_email
from app.forms import ResetPasswordForm


@app.route('/')
@app.route('/index')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
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
            prev_url=prev_url
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
            prev_url=prev_url
        )


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
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    # Получаем пользователя или возвращаем 404, если не найден
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)

    enrolled_courses = []
    teaching_courses = []
    attendance_records = []
    next_url = None
    prev_url = None

    if user.role == 'student':
        # Запрос на получение курсов, в которые записан студент
        enrolled_courses_query = sa.select(Course).join(User.enrolled_courses).where(
            User.id == user.id
        ).order_by(Course.name)
        enrolled_courses_pagination = db.paginate(
            enrolled_courses_query,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            error_out=False
        )
        enrolled_courses = enrolled_courses_pagination.items

        # Запрос на получение записей посещаемости студента
        attendance_records_query = sa.select(AttendanceRecord).where(
            AttendanceRecord.student_id == user.id
        ).order_by(AttendanceRecord.date.desc())
        attendance_records_pagination = db.paginate(
            attendance_records_query,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            error_out=False
        )
        attendance_records = attendance_records_pagination.items

        # Определяем URL для следующей и предыдущей страниц безопасно
        next_url = url_for('user', username=user.username, page=page + 1) \
            if (enrolled_courses_pagination.has_next or attendance_records_pagination.has_next) else None

        prev_url = url_for('user', username=user.username, page=page - 1) \
            if (page > 1 and (enrolled_courses_pagination.has_prev or attendance_records_pagination.has_prev)) else None

        return render_template(
            'user.html',
            user=user,
            enrolled_courses=enrolled_courses,
            attendance_records=attendance_records,
            next_url=next_url,
            prev_url=prev_url
        )

    elif user.role == 'teacher':
        # Запрос на получение курсов, которые ведет учитель
        teaching_courses_query = sa.select(Course).join(User.teaching_courses).where(
            User.id == user.id
        ).order_by(Course.name)
        teaching_courses_pagination = db.paginate(
            teaching_courses_query,
            page=page,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            error_out=False
        )
        teaching_courses = teaching_courses_pagination.items

        # Определяем URL для следующей и предыдущей страниц
        next_url = url_for('user', username=user.username, page=teaching_courses_pagination.next_num) \
            if teaching_courses_pagination.has_next else None
        prev_url = url_for('user', username=user.username, page=teaching_courses_pagination.prev_num) \
            if teaching_courses_pagination.has_prev else None

        return render_template(
            'user.html',
            user=user,
            teaching_courses=teaching_courses,
            next_url=next_url,
            prev_url=prev_url
        )

    else:
        # Для других ролей, если они есть
        return render_template('user.html', user=user)



@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Изменения сохранены.', 'success')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Редактировать профиль', form=form)

# маршруты для управления курсами и посещаемостью

@app.route('/courses')
@login_required
def courses():
    page = request.args.get('page', 1, type=int)
    all_courses_query = sa.select(Course).order_by(Course.name)
    all_courses_pagination = db.paginate(
        all_courses_query,
        page=page,
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    all_courses = all_courses_pagination.items
    next_url = url_for('courses', page=all_courses_pagination.next_num) \
        if all_courses_pagination.has_next else None
    prev_url = url_for('courses', page=all_courses_pagination.prev_num) \
        if all_courses_pagination.has_prev else None
    return render_template(
        'courses.html',
        title='Курсы',
        courses=all_courses,
        next_url=next_url,
        prev_url=prev_url
    )

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'teacher':
        flash('You are not authorized to create courses.', 'danger')
        return redirect(url_for('index'))

    form = CourseForm()
    if form.validate_on_submit():
        course = Course(name=form.name.data, description=form.description.data)
        db.session.add(course)
        db.session.commit()
        flash(f'Курс "{course.name}" успешно создан!', 'success')
        return redirect(url_for('courses'))
    return render_template('create_edit_course.html', title='Создать курс', form=form)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if current_user.role != 'teacher':
        flash('У вас нет прав на редактирование курсов.', 'danger')
        return redirect(url_for('index'))

    course = db.session.get(Course, course_id)
    if course is None:
        flash('Курс не найден.', 'warning')
        return redirect(url_for('courses'))

    form = CourseForm(original_name=course.name)
    if form.validate_on_submit():
        course.name = form.name.data
        course.description = form.description.data
        db.session.commit()
        flash(f'Курс "{course.name}" успешно обновлён!', 'success')
        return redirect(url_for('courses'))
    elif request.method == 'GET':
        form.name.data = course.name
        form.description.data = course.description
    return render_template('create_edit_course.html', title='Редактировать курс', form=form)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'teacher':
        flash('У вас нет прав на удаление курсов.', 'danger')
        return redirect(url_for('index'))

    course = db.session.get(Course, course_id)
    if course is None:
        flash('Курс не найден.', 'warning')
        return redirect(url_for('courses'))
    try:
        db.session.delete(course)
        db.session.commit()
        flash(f'Курс "{course.name}" успешно удалён!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка удаления курса: {str(e)}', 'danger')
    return redirect(url_for('courses'))

@app.route('/assign_to_course', methods=['GET', 'POST'])
@login_required
def assign_to_course():
    if current_user.role != 'teacher':
        flash('У вас нет прав назначать пользователей на курсы.', 'danger')
        return redirect(url_for('index'))

    form = AssignCourseForm()
    users = db.session.scalars(sa.select(User).order_by(User.username)).all()
    courses = db.session.scalars(sa.select(Course).order_by(Course.name)).all()
    form.user_id.choices = [(u.id, u.username) for u in users]
    form.course_id.choices = [(c.id, c.name) for c in courses]

    if form.validate_on_submit():
        user = db.session.get(User, form.user_id.data)
        course = db.session.get(Course, form.course_id.data)

        if not user or not course:
            flash('Пользователь или курс не найден.', 'warning')
            return redirect(url_for('assign_to_course'))

        try:
            if user.role == 'teacher':
                user.add_teaching_course(course)
                flash(f'Преподаватель {user.username} назначен на курс {course.name}.', 'success')
            elif user.role == 'student':
                user.enroll_in_course(course)
                flash(f'Студент {user.username} записан на курс {course.name}.', 'success')
            else:
                flash('Некорректная роль пользователя для назначения.', 'warning')
        except ValueError as e:
            flash(str(e), 'danger')
        
        return redirect(url_for('assign_to_course'))
    
    return render_template('assign_to_course.html', title='Назначить на курс', form=form)

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
            # Явно загружаем студентов, если они еще не загружены
            if not selected_course.students:
                db.session.refresh(selected_course)
            
            form.student_id.choices = [(s.id, s.username) for s in selected_course.students]
            
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

        # Проверяем, что студент записан на курс
        if not any(s.id == student.id for s in course.students):
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
        flash(f'Посещаемость отмечена: {student.username} — {course.name} — {form.status.data}.', 'success')
        return redirect(url_for('mark_attendance', course_id=course.id))

    return render_template('mark_attendance.html', title='Отметить посещаемость', form=form)

@app.route('/_get_students_for_course')
def get_students_for_course():
    course_id = request.args.get('course_id', type=int)
    if not course_id:
        return {'students': []} # Возвращаем пустой список, если course_id нет
        
    course = db.session.get(Course, course_id)
    if not course:
        return {'students': []} # Возвращаем пустой список, если курс не найден
    
    students_data = [{'id': s.id, 'username': s.username} for s in course.students]
    return {'students': students_data} # Возвращаем словарь с ключом 'students'

@app.route('/chat/<int:recipient_id>', methods=['GET', 'POST'])
@login_required
def chat(recipient_id):
    recipient = db.session.get(User, recipient_id)
    if not recipient:
        flash('Пользователь не найден.', 'warning')
        return redirect(url_for('index'))
    form = MessageForm()
    if form.validate_on_submit():
        message = Message(sender_id=current_user.id, recipient_id=recipient_id, body=form.message.data)
        db.session.add(message)
        db.session.commit()
        flash('Сообщение отправлено!', 'success')
        return redirect(url_for('chat', recipient_id=recipient_id))
    messages = db.session.execute(
        sa.select(Message)
        .where(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id)) |
            ((Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id))
        )
        .order_by(Message.timestamp.asc())
    ).scalars().all()
    return render_template('chat.html', form=form, messages=messages, recipient=recipient)

@app.route('/chat', methods=['GET'])
@login_required
def chat_list():
    users = db.session.execute(
        sa.select(User).where(User.id != current_user.id).order_by(User.username)
    ).scalars().all()
    return render_template('chat_list.html', users=users)

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
        flash('Проверьте почту: мы отправили инструкции по сбросу пароля', 'info')
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
        flash('Пароль был сброшен.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)