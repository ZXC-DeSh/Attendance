from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, Regexp
import sqlalchemy as sa
from app import db
from app.models import User, Course, Group, Room
import re


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=3, max=20, message='Имя пользователя должно быть от 3 до 20 символов'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Имя пользователя может содержать только буквы, цифры и знак подчёркивания')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[
        DataRequired(),
        Length(min=6, message='Пароль должен содержать минимум 6 символов')
    ])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Роль', choices=[('student', 'Студент'), ('teacher', 'Преподаватель'), ('admin', 'Администратор')], validators=[DataRequired()])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(
            User.username == username.data))
        if user is not None:
            raise ValidationError('Пожалуйста, используйте другое имя пользователя.')

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data))
        if user is not None:
            raise ValidationError('Пожалуйста, используйте другой адрес электронной почты.')

class EditProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[
        DataRequired(),
        Length(min=3, max=20, message='Имя пользователя должно быть от 3 до 20 символов'),
        Regexp(r'^[a-zA-Z0-9_]+$', message='Имя пользователя может содержать только буквы, цифры и знак подчёркивания')
    ])
    about_me = TextAreaField('О себе', validators=[Length(min=0, max=140)])
    submit = SubmitField('Сохранить')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == username.data))
            if user is not None:
                raise ValidationError('Пожалуйста, используйте другое имя пользователя.')

class CourseForm(FlaskForm):
    name = StringField('Название курса', validators=[
        DataRequired(),
        Length(min=3, max=100, message='Название курса должно быть от 3 до 100 символов')
    ])
    description = TextAreaField('Описание', validators=[Length(min=0, max=256)])
    submit = SubmitField('Сохранить курс')

    def __init__(self, original_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        if name.data != self.original_name:
            course = db.session.scalar(sa.select(Course).where(
                Course.name == name.data))
            if course is not None:
                raise ValidationError('Курс с таким названием уже существует.')

class MarkAttendanceForm(FlaskForm):
    student_id = SelectField('Студент', coerce=int, validators=[DataRequired()])
    course_id = SelectField('Курс', coerce=int, validators=[DataRequired()])
    status = SelectField('Статус', choices=[('present', 'Присутствует'), ('absent', 'Отсутствует'), ('late', 'Опоздал')], validators=[DataRequired()])
    notes = TextAreaField('Заметки', validators=[Length(min=0, max=256)], render_kw={"placeholder": "Дополнительные заметки"})
    submit = SubmitField('Отметить посещаемость')

    def __init__(self, *args, **kwargs):
        super(MarkAttendanceForm, self).__init__(*args, **kwargs)
        self.student_id.choices = []
        self.course_id.choices = []

class AssignCourseForm(FlaskForm):
    user_id = SelectField('Пользователь', coerce=int, validators=[DataRequired()])
    course_id = SelectField('Курс', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Назначить')

class MessageForm(FlaskForm):
    message = TextAreaField('Сообщение', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('Отправить')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Отправить письмо для сброса пароля')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Новый пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Сбросить пароль')

class NewsForm(FlaskForm):
    title = StringField('Заголовок', validators=[
        DataRequired(),
        Length(min=5, max=200, message='Заголовок должен быть от 5 до 200 символов')
    ])
    content = TextAreaField('Содержание', validators=[
        DataRequired(),
        Length(min=10, max=5000, message='Содержание должно быть от 10 до 5000 символов')
    ])
    submit = SubmitField('Опубликовать')

class CreateGroupForm(FlaskForm):
    name = StringField('Название группы', validators=[
        DataRequired(),
        Length(min=2, max=20, message='Название группы должно быть от 2 до 20 символов'),
        Regexp(r'^[А-ЯЁA-Z0-9-]+$', message='Название группы может содержать только заглавные буквы, цифры и дефис')
    ])
    specialty = SelectField('Специальность', choices=[
        ('ПКС', 'Программное обеспечение вычислительной техники и автоматизированных систем'),
        ('ИС', 'Информационные системы и программирование'),
        ('ВД', 'Веб-разработка'),
        ('КС', 'Компьютерные системы и комплексы'),
        ('ПО', 'Программирование в компьютерных системах')
    ], validators=[DataRequired()])
    course_year = IntegerField('Курс', validators=[DataRequired()], render_kw={"min": 1, "max": 5})
    group_number = IntegerField('Номер группы', validators=[DataRequired()], render_kw={"min": 1, "max": 10})
    max_students = IntegerField('Максимальное количество студентов', validators=[DataRequired()], 
                               default=25, render_kw={"min": 1, "max": 50})
    submit = SubmitField('Создать группу')

    def validate_name(self, name):
        group = db.session.scalar(sa.select(Group).where(Group.name == name.data))
        if group is not None:
            raise ValidationError('Группа с таким названием уже существует.')

    def validate_course_year(self, course_year):
        if course_year.data < 1 or course_year.data > 5:
            raise ValidationError('Курс должен быть от 1 до 5.')

    def validate_group_number(self, group_number):
        if group_number.data < 1 or group_number.data > 10:
            raise ValidationError('Номер группы должен быть от 1 до 10.')

    def validate_max_students(self, max_students):
        if max_students.data < 1 or max_students.data > 50:
            raise ValidationError('Максимальное количество студентов должно быть от 1 до 50.')

class RoomForm(FlaskForm):
    number = StringField('Номер аудитории', validators=[
        DataRequired(message='Номер аудитории обязателен'),
        Length(min=1, max=20, message='Номер аудитории должен быть от 1 до 20 символов')
    ])
    building = StringField('Корпус', validators=[
        DataRequired(message='Корпус обязателен'),
        Length(min=1, max=50, message='Название корпуса должно быть от 1 до 50 символов')
    ])
    room_type = SelectField('Тип аудитории', choices=[
        ('лекционная', 'Лекционная'),
        ('лабораторная', 'Лабораторная'),
        ('компьютерная', 'Компьютерная'),
        ('семинарская', 'Семинарская'),
        ('конференц-зал', 'Конференц-зал'),
        ('спортивный зал', 'Спортивный зал')
    ], validators=[DataRequired(message='Тип аудитории обязателен')])
    capacity = IntegerField('Вместимость', validators=[
        DataRequired(message='Вместимость обязательна')
    ])
    is_active = BooleanField('Аудитория активна', default=True)
    submit = SubmitField('Сохранить')

    def __init__(self, original_number=None, *args, **kwargs):
        super(RoomForm, self).__init__(*args, **kwargs)
        self.original_number = original_number

    def validate_number(self, number):
        if number.data != self.original_number:
            room = db.session.scalar(sa.select(Room).where(Room.number == number.data))
            if room is not None:
                raise ValidationError('Аудитория с таким номером уже существует.')

    def validate_capacity(self, capacity):
        if capacity.data < 1 or capacity.data > 500:
            raise ValidationError('Вместимость должна быть от 1 до 500 мест.')