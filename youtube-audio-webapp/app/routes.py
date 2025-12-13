from flask import Blueprint, render_template, request, redirect, url_for, flash
from .downloader import download_audio_from_urls

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        urls = request.form.get('urls')
        output_dir = request.form.get('output_dir', './downloads')
        
        if urls:
            try:
                url_list = [url.strip() for url in urls.splitlines() if url.strip()]
                download_audio_from_urls(url_list, output_dir)
                flash('Download started successfully!', 'success')
            except Exception as e:
                flash(f'Error: {str(e)}', 'danger')
        else:
            flash('Please provide at least one URL.', 'warning')
        
        return redirect(url_for('main.index'))
    
    return render_template('index.html')