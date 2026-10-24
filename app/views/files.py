import os
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

bp = Blueprint('files', __name__, url_prefix='/upload')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


@bp.route('/', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename:
            flash('Pilih file terlebih dahulu.', 'danger')
            return redirect(url_for('files.upload'))
        if not allowed_file(file.filename):
            flash('Format file harus PNG atau JPG.', 'danger')
            return redirect(url_for('files.upload'))

        # Prefix acak supaya file dengan nama sama tidak saling timpa
        filename = f'{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}'
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        flash(f'File "{filename}" berhasil diupload.', 'success')
        return redirect(url_for('files.upload'))

    return render_template('upload-file.html')
