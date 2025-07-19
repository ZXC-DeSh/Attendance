from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5

# Таблица связей между учителями и курсами, которые они преподают
teacher_course_association = sa.Table(
    'teacher_course_association',
    db.metadata,
    sa.Column('teacher_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('course_id', sa.Integer, sa.ForeignKey('course.id'), primary_key=True)
)

# Таблица связей между учениками и курсами, на которые они записаны
student_course_association = sa.Table(
    'student_course_association',
    db.metadata,
    sa.Column('student_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('course_id', sa.Integer, sa.ForeignKey('course.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    
    # Добавляем поле для роли пользователя: 'student' или 'teacher'
    role: so.Mapped[str] = so.mapped_column(sa.String(20), default='student') 

    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(
        default=lambda: datetime.now(timezone.utc))

    # Связь для учителей и курсов, которые они преподают (многие ко многим)
    # Если user.role == 'teacher'
    teaching_courses: so.WriteOnlyMapped['Course'] = so.relationship(
        secondary=teacher_course_association,
        back_populates='teachers'
    )

    # Связь для учеников и курсов, на которые они записаны (многие ко многим)
    # Если user.role == 'student'
    enrolled_courses: so.WriteOnlyMapped['Course'] = so.relationship(
        secondary=student_course_association,
        back_populates='students'
    )

    # Связь с записями о посещаемости (только для студентов)
    attendance_records: so.WriteOnlyMapped['AttendanceRecord'] = so.relationship(
        back_populates='student',
        cascade="all, delete-orphan" # Удалять записи о посещаемости при удалении студента
    )

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    # Методы для управления курсами (для учителей)
    def add_teaching_course(self, course):
        if self.role == 'teacher' and course not in self.teaching_courses:
            self.teaching_courses.append(course) # Используем append для коллекций

    def remove_teaching_course(self, course):
        if self.role == 'teacher' and course in self.teaching_courses:
            self.teaching_courses.remove(course) # Используем remove для коллекций

    # Методы для управления курсами (для студентов)
    def enroll_in_course(self, course):
        if self.role == 'student' and course not in self.enrolled_courses:
            self.enrolled_courses.add(course)

    def unenroll_from_course(self, course):
        if self.role == 'student' and course in self.enrolled_courses:
            self.enrolled_courses.remove(course)

class Post(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    author: so.Mapped[User] = so.relationship(back_populates='posts')

    def __repr__(self):
        return '<Post {}>'.format(self.body)

class Course(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), unique=True, index=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    # Связь с учителями, которые преподают этот курс
    teachers: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=teacher_course_association,
        back_populates='teaching_courses'
    )

    # Связь с учениками, записанными на этот курс
    students: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=student_course_association,
        back_populates='enrolled_courses'
    )

    # Связь с записями о посещаемости для этого курса
    attendance_records: so.WriteOnlyMapped['AttendanceRecord'] = so.relationship(
        back_populates='course',
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<Course {self.name}>'

class AttendanceRecord(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    
    # Связь с учеником
    student_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    student: so.Mapped['User'] = so.relationship(back_populates='attendance_records')

    # Связь с курсом
    course_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('course.id'), index=True)
    course: so.Mapped['Course'] = so.relationship(back_populates='attendance_records')

    date: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    
    # Статус посещаемости: 'present', 'absent', 'late', 'excused'
    status: so.Mapped[str] = so.mapped_column(sa.String(20), default='present') 
    notes: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    def __repr__(self):
        return f'<AttendanceRecord for {self.student.username} on {self.course.name} at {self.date.strftime("%Y-%m-%d %H:%M")}>'
    
@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))
