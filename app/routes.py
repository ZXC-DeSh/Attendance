from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, CourseForm, MarkAttendanceForm, AssignCourseForm
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from app.models import User, Post, Course, AttendanceRecord
from urllib.parse import urlsplit
from datetime import datetime, timezone

@app.route('/')
@app.route('/index')
@login_required
def index():
    if current_user.role == 'student':
        attendance_records = db.session.scalars(
            sa.select(AttendanceRecord)
            .where(AttendanceRecord.student_id == current_user.id)
            .order_by(AttendanceRecord.date.desc())
        ).all()
        return render_template('index.html', title='Главная', attendance_records=attendance_records)
    else: # Для учителей или других ролей
        teaching_courses = db.session.scalars(
            sa.select(Course)
            .join(User.teaching_courses)
            .where(User.id == current_user.id)
        ).all()
        return render_template('index.html', title='Главная', teaching_courses=teaching_courses)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

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
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    
    enrolled_courses = []
    teaching_courses = []
    posts = [] # Инициализируем posts, чтобы избежать ошибки в шаблоне, если он используется

    if user.role == 'student':
        enrolled_courses = db.session.scalars(
            sa.select(Course)
            .join(User.enrolled_courses)
            .where(User.id == user.id)
        ).all()
        attendance_records = db.session.scalars(
            sa.select(AttendanceRecord)
            .where(AttendanceRecord.student_id == user.id)
            .order_by(AttendanceRecord.date.desc())
        ).all()
        return render_template('user.html', user=user, enrolled_courses=enrolled_courses, attendance_records=attendance_records, posts=posts)
    elif user.role == 'teacher':
        teaching_courses = db.session.scalars(
            sa.select(Course)
            .join(User.teaching_courses)
            .where(User.id == user.id)
        ).all()
        return render_template('user.html', user=user, teaching_courses=teaching_courses, posts=posts)
    else:
        return render_template('user.html', user=user, posts=posts) # Для других ролей


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
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form)

# маршруты для управления курсами и посещаемостью

@app.route('/courses')
@login_required
def courses():
    all_courses = db.session.scalars(sa.select(Course)).all()
    return render_template('courses.html', title='Courses', courses=all_courses)

@app.route('/create_course', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'teacher':
        flash('You are not authorized to create courses.')
        return redirect(url_for('index'))

    form = CourseForm()
    if form.validate_on_submit():
        course = Course(name=form.name.data, description=form.description.data)
        db.session.add(course)
        db.session.commit()
        flash(f'Course "{course.name}" created successfully!')
        return redirect(url_for('courses'))
    return render_template('create_edit_course.html', title='Create Course', form=form)

@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if current_user.role != 'teacher':
        flash('You are not authorized to edit courses.')
        return redirect(url_for('index'))

    course = db.session.get(Course, course_id)
    if course is None:
        flash('Course not found.')
        return redirect(url_for('courses'))

    form = CourseForm(original_name=course.name)
    if form.validate_on_submit():
        course.name = form.name.data
        course.description = form.description.data
        db.session.commit()
        flash(f'Course "{course.name}" updated successfully!')
        return redirect(url_for('courses'))
    elif request.method == 'GET':
        form.name.data = course.name
        form.description.data = course.description
    return render_template('create_edit_course.html', title='Edit Course', form=form)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'teacher':
        flash('You are not authorized to delete courses.')
        return redirect(url_for('index'))

    course = db.session.get(Course, course_id)
    if course is None:
        flash('Course not found.')
        return redirect(url_for('courses'))
    
    db.session.delete(course)
    db.session.commit()
    flash(f'Course "{course.name}" deleted successfully!')
    return redirect(url_for('courses'))

@app.route('/assign_to_course', methods=['GET', 'POST'])
@login_required
def assign_to_course():
    if current_user.role != 'teacher':
        flash('You are not authorized to assign users to courses.')
        return redirect(url_for('index'))

    form = AssignCourseForm()
    
    # Заполняем поля выбора динамически
    users = db.session.scalars(sa.select(User).order_by(User.username)).all()
    form.user_id.choices = [(u.id, u.username) for u in users]
    
    courses = db.session.scalars(sa.select(Course).order_by(Course.name)).all()
    form.course_id.choices = [(c.id, c.name) for c in courses]

    if form.validate_on_submit():
        user_to_assign = db.session.get(User, form.user_id.data)
        course_to_assign = db.session.get(Course, form.course_id.data)

        if not user_to_assign or not course_to_assign:
            flash('Invalid user or course selected.')
            return redirect(url_for('assign_to_course'))

        if user_to_assign.role == 'teacher':
            if course_to_assign not in user_to_assign.teaching_courses:
                user_to_assign.add_teaching_course(course_to_assign)
                db.session.commit()
                flash(f'Teacher {user_to_assign.username} assigned to course {course_to_assign.name}.')
            else:
                flash(f'Teacher {user_to_assign.username} is already assigned to course {course_to_assign.name}.')
        elif user_to_assign.role == 'student':
            if course_to_assign not in user_to_assign.enrolled_courses:
                user_to_assign.enroll_in_course(course_to_assign)
                db.session.commit()
                flash(f'Student {user_to_assign.username} enrolled in course {course_to_assign.name}.')
            else:
                flash(f'Student {user_to_assign.username} is already enrolled in course {course_to_assign.name}.')
        else:
            flash('Cannot assign this user role to a course.')
        
        return redirect(url_for('assign_to_course'))
    
    return render_template('assign_to_course.html', title='Assign User to Course', form=form)

@app.route('/mark_attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role != 'teacher':
        flash('You are not authorized to mark attendance.')
        return redirect(url_for('index'))

    form = MarkAttendanceForm()

    teacher_courses = db.session.scalars(
        sa.select(Course)
        .join(User.teaching_courses)
        .where(User.id == current_user.id)
    ).all()
    form.course_id.choices = [(c.id, c.name) for c in teacher_courses]

    selected_course_id = request.args.get('course_id', type=int)
    if selected_course_id:
        selected_course = db.session.get(Course, selected_course_id)
        if selected_course:
            form.student_id.choices = [(s.id, s.username) for s in selected_course.students]
        else:
            form.student_id.choices = []
    else:
        form.student_id.choices = []

    if form.validate_on_submit():
        student = db.session.get(User, form.student_id.data)
        course = db.session.get(Course, form.course_id.data)

        if not student or not course:
            flash('Invalid student or course selected.')
            return redirect(url_for('mark_attendance'))
        
        if student.role != 'student':
            flash('Only students can have attendance records.')
            return redirect(url_for('mark_attendance'))

        # Проверяем, что студент записан на этот курс
        is_student_enrolled = db.session.scalar(
            sa.select(sa.exists().where(
                User.id == student.id,
                User.enrolled_courses.contains(course)
            ))
        )
        if not is_student_enrolled:
            flash(f'Student {student.username} is not enrolled in course {course.name}.')
            return redirect(url_for('mark_attendance'))

        # Проверяем, что учитель преподает этот курс
        is_teacher_teaching = db.session.scalar(
            sa.select(sa.exists().where(
                User.id == current_user.id,
                User.teaching_courses.contains(course)
            ))
        )
        if not is_teacher_teaching:
            flash(f'You are not authorized to mark attendance for course {course.name}.')
            return redirect(url_for('mark_attendance'))

        attendance_record = AttendanceRecord(
            student=student,
            course=course,
            status=form.status.data,
            notes=form.notes.data
        )
        db.session.add(attendance_record)
        db.session.commit()
        flash(f'Attendance marked for {student.username} in {course.name} as {form.status.data}.')
        return redirect(url_for('mark_attendance', course_id=course.id))

    if request.method == 'GET' and selected_course_id:
        form.course_id.data = selected_course_id

    return render_template('mark_attendance.html', title='Mark Attendance', form=form)


# AJAX-маршрут для обновления списка студентов при выборе курса
@app.route('/_get_students_for_course')
def get_students_for_course():
    course_id = request.args.get('course_id', type=int)
    students_data = []
    if course_id:
        course = db.session.get(Course, course_id)
        if course:
            students_data = [{'id': s.id, 'username': s.username} for s in course.students]
    return {'students': students_data}
