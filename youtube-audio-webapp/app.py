"""
YouTube Audio Downloader - Flask Web UI
"""

import os
import sys
import logging
import threading
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import yt_dlp

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'

# Global state for download progress
download_status = {
    'is_downloading': False,
    'current_video': '',
    'progress': 0,
    'total_videos': 0,
    'completed': 0,
    'failed': 0,
    'logs': [],
    'download_urls': []
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_directories():
    """Create necessary directories."""
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.config['DOWNLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)


def add_log(message, level='info'):
    """Add a log message to the status."""
    timestamp = time.strftime('%H:%M:%S')
    download_status['logs'].append({
        'timestamp': timestamp,
        'message': message,
        'level': level
    })
    # Keep only last 100 logs
    if len(download_status['logs']) > 100:
        download_status['logs'] = download_status['logs'][-100:]


def progress_hook(d):
    """Hook for yt-dlp progress updates."""
    if d['status'] == 'downloading':
        try:
            percent = d.get('_percent_str', '0%').strip()
            download_status['progress'] = float(percent.replace('%', ''))
        except (ValueError, TypeError):
            pass
    elif d['status'] == 'finished':
        download_status['progress'] = 100


def extract_playlist_urls(playlist_url):
    """Extract individual video URLs from a playlist."""
    add_log(f"Extracting playlist: {playlist_url}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'ignoreerrors': True,
    }
    
    urls = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            
            if info:
                if info.get('_type') == 'playlist' and 'entries' in info:
                    add_log(f"Found playlist: {info.get('title', 'Unknown')}")
                    for entry in info['entries']:
                        if entry is None:
                            continue
                        
                        video_id = entry.get('id')
                        video_url = entry.get('url')
                        
                        if video_url:
                            urls.append(video_url)
                        elif video_id:
                            urls.append(f"https://www.youtube.com/watch?v={video_id}")
                
                elif info.get('id'):
                    urls.append(f"https://www.youtube.com/watch?v={info['id']}")
        
        add_log(f"Found {len(urls)} videos")
        return urls
        
    except Exception as e:
        add_log(f"Error extracting playlist: {str(e)}", 'error')
        return []


def download_audio_thread(urls, output_dir):
    """Download audio in a separate thread."""
    download_status['is_downloading'] = True
    download_status['total_videos'] = len(urls)
    download_status['completed'] = 0
    download_status['failed'] = 0
    download_status['current_video'] = ''
    download_status['progress'] = 0
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'ignoreerrors': True,
        'no_warnings': False,
        'progress_hooks': [progress_hook],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(urls, 1):
            title = 'Unknown Title'  # Initialize here
            try:
                download_status['progress'] = 0
                add_log(f"Processing video {i}/{len(urls)}")
                
                info = ydl.extract_info(url, download=False)
                if info:
                    title = info.get('title', 'Unknown Title')
                    download_status['current_video'] = title
                    add_log(f"Downloading: {title}")
                
                ydl.download([url])
                download_status['completed'] += 1
                add_log(f"✓ Completed: {title}", 'success')
                
            except Exception as e:
                download_status['failed'] += 1
                add_log(f"✗ Failed: {title} - {str(e)}", 'error')
    
    # Get list of downloaded files
    download_status['download_urls'] = []
    if os.path.exists(output_dir):
        for file in os.listdir(output_dir):
            if file.endswith('.mp3'):
                download_status['download_urls'].append(file)
    
    download_status['is_downloading'] = False
    download_status['current_video'] = ''
    download_status['progress'] = 0
    add_log(f"Download complete! {download_status['completed']} succeeded, {download_status['failed']} failed", 'success')


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/download', methods=['POST'])
def start_download():
    """Start a download process."""
    if download_status['is_downloading']:
        return jsonify({'error': 'Download already in progress'}), 400
    
    data = request.json
    input_type = data.get('type')
    urls = []
    
    try:
        if input_type == 'single':
            url = data.get('url', '').strip()
            if not url:
                return jsonify({'error': 'No URL provided'}), 400
            urls = [url]
            
        elif input_type == 'playlist':
            playlist_url = data.get('url', '').strip()
            if not playlist_url:
                return jsonify({'error': 'No playlist URL provided'}), 400
            urls = extract_playlist_urls(playlist_url)
            
        elif input_type == 'multiple':
            url_text = data.get('urls', '').strip()
            if not url_text:
                return jsonify({'error': 'No URLs provided'}), 400
            urls = [line.strip() for line in url_text.split('\n') if line.strip() and not line.startswith('#')]
        
        if not urls:
            return jsonify({'error': 'No valid URLs found'}), 400
        
        # Clear previous logs and downloads
        download_status['logs'] = []
        download_status['download_urls'] = []
        
        # Start download in background thread
        thread = threading.Thread(target=download_audio_thread, args=(urls, app.config['DOWNLOAD_FOLDER']))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': f'Started downloading {len(urls)} video(s)'})
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def get_status():
    """Get current download status."""
    return jsonify(download_status)


@app.route('/api/download/<filename>')
def download_file(filename):
    """Download a completed MP3 file."""
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], safe_filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear')
def clear_downloads():
    """Clear all downloaded files."""
    try:
        download_dir = app.config['DOWNLOAD_FOLDER']
        if os.path.exists(download_dir):
            for file in os.listdir(download_dir):
                if file.endswith('.mp3'):
                    os.remove(os.path.join(download_dir, file))
        
        download_status['download_urls'] = []
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    create_directories()
    print("\n" + "="*60)
    print("YouTube Audio Downloader - Web UI")
    print("="*60)
    print("Starting server at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)