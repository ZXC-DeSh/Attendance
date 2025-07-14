from flask import render_template
from app import app

@app.route('/')
@app.route('/index')
def index():
    user = {'username':'Egor'}
    posts = [
            {
                'author' : {'username' : 'Олег'},
                'body' : 'Присутствовал на лекции по Математике.'
            },
            {
                'author' : {'username' : 'Анна'},
                'body' : 'Отсутствовала на семинаре по Физике (болезнь).'
            },
            {
                'author' : {'username' : 'Иван'},
                'body' : 'Присутствовал на практическом занятии по Программированию.'
            }
        ]

    return render_template('index.html', title='Главная', user=user, posts=posts)