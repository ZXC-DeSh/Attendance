from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length
import sqlalchemy as sa
from app import db
from app.models import User, Course


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Роль', choices=[('student', 'Студент'), ('teacher', 'Преподаватель')], validators=[DataRequired()])
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
    username = StringField('Имя пользователя', validators=[DataRequired()])
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
    name = StringField('Название курса', validators=[DataRequired()])
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