import os
from flask import Flask, render_template
from flask_cors import CORS
from backend.app.config import Config
from backend.app.db import init_db_pool

def create_app(config_class=Config):
    # Base directory for locating templates and static assets
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir
    )
    app.config.from_object(config_class)

    # Enable Cross-Origin Resource Sharing for API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database Connection Pool
    with app.app_context():
        try:
            init_db_pool()
        except Exception as e:
            app.logger.error(f"Could not connect to database on startup: {e}")

    # Register Blueprints
    from backend.app.routes.auth_routes import auth_bp
    from backend.app.routes.customer_routes import customer_bp
    from backend.app.routes.employee_routes import employee_bp
    from backend.app.routes.admin_routes import admin_bp
    from backend.app.routes.api_routes import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Jinja Template Context Processors & Filters
    @app.context_processor
    def inject_shop_context():
        from backend.app.services.settings_service import get_shop_settings
        from backend.app.utils.decorators import get_current_user
        try:
            shop = get_shop_settings()
        except Exception:
            shop = {'shop_name': 'Fresh Cut Meat Shop', 'currency_symbol': '₹'}
        current_u = get_current_user()
        return {'shop_info': shop, 'current_user': current_u}

    @app.template_filter('currency')
    def currency_filter(value):
        try:
            val = float(value)
            return f"₹{val:,.2f}"
        except Exception:
            return f"₹{value}"

    @app.template_filter('qty')
    def qty_filter(value, unit='KG'):
        try:
            val = float(value)
            if unit == 'PCS':
                return f"{int(val)} PCS"
            return f"{val:.3f} KG"
        except Exception:
            return f"{value} {unit}"

    # Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('403.html'), 403

    return app

