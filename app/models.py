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

teacher_course_association = sa.Table(
    'teacher_course_association',
    db.metadata,
    sa.Column('teacher_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('course_id', sa.Integer, sa.ForeignKey('course.id'), primary_key=True)
)

student_course_association = sa.Table(
    'student_course_association',
    db.metadata,
    sa.Column('student_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('course_id', sa.Integer, sa.ForeignKey('course.id'), primary_key=True)
)

user_favorites_association = sa.Table(
    'user_favorites',
    db.metadata,
    sa.Column('user_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('course_id', sa.Integer, sa.ForeignKey('course.id'), primary_key=True)
)

student_group_association = sa.Table(
    'student_group_association',
    db.metadata,
    sa.Column('student_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('group_id', sa.Integer, sa.ForeignKey('group.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    role: so.Mapped[str] = so.mapped_column(sa.String(20), default='student')
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    
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
    
    favorite_courses: so.Mapped[List['Course']] = so.relationship(
        secondary=user_favorites_association,
        back_populates='favorited_by',
        collection_class=list
    )
    
    group: so.Mapped[Optional['Group']] = so.relationship(
        secondary=student_group_association,
        back_populates='students',
        uselist=False
    )
    
    attendance_records: so.WriteOnlyMapped['AttendanceRecord'] = so.relationship(
        back_populates='student',
        cascade="all, delete-orphan"
    )
    
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

    def is_admin(self) -> bool:
        return self.role == 'admin'
    
    def is_teacher(self) -> bool:
        return self.role == 'teacher'
    
    def is_student(self) -> bool:
        return self.role == 'student'

    def add_teaching_course(self, course: 'Course') -> None:
        if self.role != 'teacher':
            raise ValueError("Only teachers can be assigned to teaching courses")
        if course not in self.teaching_courses:
            self.teaching_courses.append(course)

    def remove_teaching_course(self, course: 'Course') -> None:
        if course in self.teaching_courses:
            self.teaching_courses.remove(course)

    def enroll_in_course(self, course: 'Course') -> None:
        if self.role != 'student':
            raise ValueError("Only students can enroll in courses")
        if course not in self.enrolled_courses:
            self.enrolled_courses.append(course)

    def unenroll_from_course(self, course: 'Course') -> None:
        if course in self.enrolled_courses:
            self.enrolled_courses.remove(course)

    def add_favorite_course(self, course: 'Course') -> None:
        if course not in self.favorite_courses:
            self.favorite_courses.append(course)

    def remove_favorite_course(self, course: 'Course') -> None:
        if course in self.favorite_courses:
            self.favorite_courses.remove(course)

    def is_course_favorite(self, course: 'Course') -> bool:
        return course in self.favorite_courses

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

class Group(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(20), unique=True, index=True)
    specialty: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    course_year: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=False)
    group_number: so.Mapped[int] = so.mapped_column(sa.Integer, nullable=False)
    max_students: so.Mapped[int] = so.mapped_column(sa.Integer, default=25)
    created_at: so.Mapped[datetime] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    
    students: so.Mapped[List['User']] = so.relationship(
        secondary=student_group_association,
        back_populates='group',
        collection_class=list
    )
    
    def __repr__(self) -> str:
        return f'<Group {self.name}>'
    
    @property
    def current_students_count(self) -> int:
        return len(self.students)
    
    @property
    def is_full(self) -> bool:
        return self.current_students_count >= self.max_students

class Course(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), unique=True, index=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

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
    
    favorited_by: so.Mapped[List['User']] = so.relationship(
        secondary=user_favorites_association,
        back_populates='favorite_courses',
        collection_class=list
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

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), nullable=False, unique=True)
    capacity = db.Column(db.Integer, nullable=False)
    building = db.Column(db.String(50), nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Room {self.number}>'

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    slot_number = db.Column(db.Integer, nullable=False)
    week_type = db.Column(db.String(10), default='all')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group = db.relationship('Group', backref='schedules')
    course = db.relationship('Course', backref='schedules')
    teacher = db.relationship('User', backref='teaching_schedules')
    room = db.relationship('Room', backref='schedules')

    def __repr__(self):
        return f'<Schedule {self.group.name} {self.course.name} {self.day_of_week}:{self.slot_number}>'

class TeacherSubstitution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    substitute_teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200))
    is_confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    original_schedule = db.relationship('Schedule', backref='substitutions')
    substitute_teacher = db.relationship('User', backref='substitutions')

    def __repr__(self):
        return f'<TeacherSubstitution {self.original_schedule} -> {self.substitute_teacher.username}>'

@login.user_loader
def load_user(id: int) -> Optional[User]:
    return db.session.get(User, id)