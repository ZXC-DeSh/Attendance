from datetime import datetime, timezone
from typing import Optional, List
import sqlalchemy as sa
import sqlalchemy.orm as so
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import login
from hashlib import md5
from time import time
import jwt
from app import app

class Message(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    sender_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), nullable=False)
    recipient_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), nullable=False)
    body: so.Mapped[str] = so.mapped_column(sa.String(1000), nullable=False)
    timestamp: so.Mapped[datetime] = so.mapped_column(sa.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    
    sender: so.Mapped['User'] = so.relationship('User', foreign_keys=[sender_id], back_populates='sent_messages')
    recipient: so.Mapped['User'] = so.relationship('User', foreign_keys=[recipient_id], back_populates='received_messages')
    
    def __repr__(self) -> str:
        return f'<Message {self.body}>'

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
    role: so.Mapped[str] = so.mapped_column(sa.String(20), default='student')
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    
    # Связи
    sent_messages: so.Mapped[List['Message']] = so.relationship(
        'Message', 
        foreign_keys='Message.sender_id',
        back_populates='sender'
    )
    received_messages: so.Mapped[List['Message']] = so.relationship(
        'Message', 
        foreign_keys='Message.recipient_id',
        back_populates='recipient'
    )
    
    teaching_courses: so.Mapped[List['Course']] = so.relationship(
        secondary=teacher_course_association,
        back_populates='teachers',
        collection_class=list
    )
    
    enrolled_courses: so.Mapped[List['Course']] = so.relationship(
        secondary=student_course_association,
        back_populates='students',
        collection_class=list,
        lazy='joined'
    )
    attendance_records: so.WriteOnlyMapped['AttendanceRecord'] = so.relationship(
        back_populates='student',
        cascade="all, delete-orphan"
    )
    
    # Связь с новостями (для администраторов)
    news_posts: so.Mapped[List['News']] = so.relationship(
        back_populates='author',
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f'<User {self.username}>'
    
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def avatar(self, size: int) -> str:
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    # Методы для проверки ролей
    def is_admin(self) -> bool:
        return self.role == 'admin'
    
    def is_teacher(self) -> bool:
        return self.role == 'teacher'
    
    def is_student(self) -> bool:
        return self.role == 'student'

        # Методы для управления курсами (для учителей)
    def add_teaching_course(self, course: 'Course') -> None:
        if self.role != 'teacher':
            raise ValueError("Only teachers can be assigned to teaching courses")
        if course not in self.teaching_courses:
            self.teaching_courses.append(course)

    def remove_teaching_course(self, course: 'Course') -> None:
        if course in self.teaching_courses:
            self.teaching_courses.remove(course)

    # Методы для управления курсами (для студентов)
    def enroll_in_course(self, course: 'Course') -> None:
        if self.role != 'student':
            raise ValueError("Only students can enroll in courses")
        if course not in self.enrolled_courses:
            self.enrolled_courses.append(course)

    def unenroll_from_course(self, course: 'Course') -> None:
        if course in self.enrolled_courses:
            self.enrolled_courses.remove(course)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except Exception:
            return
        return db.session.get(User, id)

class Course(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), unique=True, index=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    is_favorite: so.Mapped[bool] = so.mapped_column(default=False)

    # Связи
    teachers: so.Mapped[List['User']] = so.relationship(
        secondary=teacher_course_association,
        back_populates='teaching_courses',
        collection_class=list
    )
    
    students: so.Mapped[List['User']] = so.relationship(
        secondary=student_course_association,
        back_populates='enrolled_courses',
        collection_class=list,
        lazy='joined'
    )

    attendance_records: so.WriteOnlyMapped['AttendanceRecord'] = so.relationship(
        back_populates='course',
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f'<Course {self.name}>'

class AttendanceRecord(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    student_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), index=True)
    student: so.Mapped['User'] = so.relationship(back_populates='attendance_records')
    course_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('course.id'), index=True)
    course: so.Mapped['Course'] = so.relationship(back_populates='attendance_records')
    date: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    status: so.Mapped[str] = so.mapped_column(sa.String(20), default='present')
    notes: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    def __repr__(self) -> str:
        return f'<AttendanceRecord for {self.student.username} on {self.course.name} at {self.date.strftime("%Y-%m-%d %H:%M")}>'

class News(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(200), nullable=False)
    content: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)
    author_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey('user.id'), nullable=False)
    author: so.Mapped['User'] = so.relationship(back_populates='news_posts')
    created_at: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: so.Mapped[Optional[datetime]] = so.mapped_column(default=None, onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self) -> str:
        return f'<News {self.title} by {self.author.username}>'

@login.user_loader
def load_user(id: int) -> Optional[User]:
    return db.session.get(User, id)