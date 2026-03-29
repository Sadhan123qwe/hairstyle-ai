import os
from flask import Flask, render_template, session, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from config import Config
from database import get_db

bcrypt = Bcrypt()


def create_app():
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(Config)
    bcrypt.init_app(app)

    # Test MongoDB connection at startup
    database = get_db()
    if database is None:
        print("[WARNING] MongoDB not connected at startup. Auth will be unavailable.")
    else:
        print("[INFO] MongoDB ready.")

    # Register Blueprints
    from routes.auth import auth_bp, init_auth
    from routes.analysis import analysis_bp, init_analysis
    from routes.chatbot import chatbot_bp

    init_auth(bcrypt)
    init_analysis()

    app.register_blueprint(auth_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(chatbot_bp)

    # Main Blueprint (inline)
    from flask import Blueprint
    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        return render_template('index.html')

    @main_bp.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        user = None
        recent_history = []
        current_db = get_db()
        if current_db is not None:
            try:
                from bson import ObjectId
                user = current_db.users.find_one({'_id': ObjectId(session['user_id'])})
                recent_history = list(current_db.analysis_history.find(
                    {'user_id': session['user_id']}
                ).sort('analyzed_at', -1).limit(5))
                for item in recent_history:
                    item['_id'] = str(item['_id'])
            except Exception as e:
                print(f"[ERROR] Dashboard: {e}")
        return render_template('dashboard.html', user=user, recent_history=recent_history)

    @main_bp.route('/about')
    def about():
        return render_template('about.html')

    app.register_blueprint(main_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    @app.errorhandler(413)
    def too_large(e):
        flash('File too large. Max 16MB.', 'error')
        return redirect(url_for('analysis.analyze')), 302

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
