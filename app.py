import os
import shutil
import tempfile
import logging
from flask import Flask, request, jsonify, render_template, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# Save downloaded audio in /downloads inside the container as requested
DOWNLOAD_DIR = '/downloads'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    # 1. Validate request
    data = request.json
    if not data or 'youtube_url' not in data:
        return jsonify({"error": "Invalid request: missing youtube_url"}), 400

    url = data['youtube_url'].strip()
    if not url:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    # 2. Prepare temporary download directory
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    temp_dir = tempfile.mkdtemp(dir=DOWNLOAD_DIR)

    # 3. Setup yt-dlp to download bestaudio and convert to mp3 via ffmpeg
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': ['player_client=android']  # Bypass YouTube 403 Forbidden
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Pre-flight check: extract info first to catch invalid URLs
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    logger.error("yt-dlp returned no info for URL")
                    raise Exception("Could not extract video information")
            except Exception as e:
                shutil.rmtree(temp_dir)
                logger.error(f"yt-dlp extract error: {e}")
                return jsonify({"error": "yt-dlp fails: Invalid URL or video unavailable"}), 400

            # Actually download and convert
            ydl.download([url])

        # 4. Check for successful conversion
        files = os.listdir(temp_dir)
        mp3_file = next((f for f in files if f.endswith('.mp3')), None)
        
        if not mp3_file:
            shutil.rmtree(temp_dir)
            logger.error("FFmpeg conversion failed: No MP3 produced in temp dir")
            return jsonify({"error": "FFmpeg conversion fails"}), 500

        mp3_path = os.path.join(temp_dir, mp3_file)

        # 5. Clean up temporary files *after* sending them to the user
        @after_this_request
        def cleanup(response):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Error removing temp dir {temp_dir}: {e}")
            return response

        # 6. Send MP3 file as response
        return send_file(
            mp3_path, 
            as_attachment=True, 
            download_name=mp3_file, 
            mimetype="audio/mpeg"
        )

    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)