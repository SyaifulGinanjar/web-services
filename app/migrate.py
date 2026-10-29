"""Migrasi SQL sederhana: `flask migrate` menjalankan file migrations/*.sql yang belum pernah dijalankan."""
from pathlib import Path

import click
from flask import current_app

from app.db import get_db

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / 'migrations'


def pending_migrations(applied):
    return [path for path in sorted(MIGRATIONS_DIR.glob('*.sql')) if path.name not in applied]


def split_statements(sql):
    lines = [line for line in sql.splitlines() if not line.strip().startswith('--')]
    return [stmt.strip() for stmt in '\n'.join(lines).split(';') if stmt.strip()]


def register(app):
    @app.cli.command('migrate')
    @click.option('--dry-run', is_flag=True, help='Tampilkan migrasi yang akan dijalankan tanpa mengeksekusi.')
    def migrate(dry_run):
        """Jalankan migrasi database yang belum diterapkan."""
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("show tables like 'schema_migrations'")
            exists = cursor.fetchone() is not None
            if not exists and not dry_run:
                cursor.execute('''create table schema_migrations (
                                      name varchar(255) primary key,
                                      applied_at timestamp default current_timestamp)''')
            applied = set()
            if exists:
                cursor.execute('select name from schema_migrations')
                applied = {row['name'] for row in cursor.fetchall()}
        db.commit()

        pending = pending_migrations(applied)
        if not pending:
            click.echo('Database sudah up to date.')
            return

        click.echo(f'Database: {current_app.config["DB_NAME"]} @ {current_app.config["DB_HOST"]}')
        for path in pending:
            click.echo(f'{"[dry-run] " if dry_run else ""}Menjalankan {path.name}')
            if dry_run:
                continue
            # DDL MySQL auto-commit per statement; satu file = satu perubahan supaya mudah diulang bila gagal
            with db.cursor() as cursor:
                for statement in split_statements(path.read_text(encoding='utf-8')):
                    cursor.execute(statement)
                cursor.execute('insert into schema_migrations (name) values (%s)', (path.name,))
            db.commit()
        click.echo('Selesai.')
