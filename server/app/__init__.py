from flask import Flask, g
from config import config
from flask_cors import CORS, cross_origin


def create_app(config_name):
    app = Flask(__name__)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # CORS(app, supports_credentials=True, origins=app.config.get('ORIGINS'))
    CORS(app, supports_credentials=True, origins='*')

    @app.before_request
    def before_request():
        g.secret_key = app.config.get('SECRET_KEY')
        g.root_wallet_priv_key = app.config.get('ROOT_WALLET_PRIV_KEY')
        g.db = app.config.get('DATABASE_URL')
        g.ipfs = app.config.get('IPFS_URL')
        g.file_size_limit = app.config.get('FILE_SIZE_LIMIT')
        g.page_title_limit = app.config.get('PAGE_TITLE_LIMIT')
        g.page_descr_limit = app.config.get('PAGE_DESCR_LIMIT')

    if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
        from flask_sslify import SSLify
        ssslify = SSLify(app)

    from main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api_v1_0 import api as api_v1_0_blueprint
    app.register_blueprint(api_v1_0_blueprint, url_prefix='/api/v1.0')

    return app
