from flask import render_template
from app import app, db

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    try:
        db.session.rollback()
    except:
        pass  # Если не удалось откатить, просто продолжим
    return render_template('errors/500.html'), 500
