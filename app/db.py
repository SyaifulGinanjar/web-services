import pymysql
from flask import current_app, g
from pymysql.cursors import DictCursor


def get_db():
    """Satu koneksi per request, otomatis ditutup di teardown."""
    if 'db' not in g:
        cfg = current_app.config
        g.db = pymysql.connect(
            host=cfg['DB_HOST'],
            port=cfg['DB_PORT'],
            user=cfg['DB_USER'],
            password=cfg['DB_PASSWORD'],
            database=cfg['DB_NAME'],
            connect_timeout=cfg['DB_CONNECT_TIMEOUT'],
            cursorclass=DictCursor,
            charset='utf8mb4',
            autocommit=False,
        )
    return g.db


def close_db(exc=None):
    db = g.pop('db', None)
    if db is None:
        return
    try:
        if exc is not None:
            db.rollback()
    finally:
        db.close()


def fetch_all(query, params=()):
    with get_db().cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def fetch_one(query, params=()):
    with get_db().cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def execute(query, params=()):
    """Jalankan INSERT/UPDATE/DELETE lalu commit. Return lastrowid."""
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute(query, params)
            lastrowid = cursor.lastrowid
        db.commit()
        return lastrowid
    except Exception:
        db.rollback()
        raise


def init_app(app):
    app.teardown_appcontext(close_db)
