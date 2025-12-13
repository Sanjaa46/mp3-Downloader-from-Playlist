"""
YouTube Audio Downloader Web Application
Core functionality for downloading audio from YouTube.
"""

import os
import logging
from flask import current_app
import yt_dlp

def get_ydl_opts(output_dir):
    """Get yt-dlp options for audio download."""
    return {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'ignoreerrors': True,
        'no_warnings': False,
    }

def download_audio(urls, output_dir):
    """Download audio from YouTube URLs."""
    ydl_opts = get_ydl_opts(output_dir)
    successful_downloads = 0
    failed_downloads = 0
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for url in urls:
            try:
                logging.info(f"Processing: {url}")
                ydl.download([url])
                successful_downloads += 1
                logging.info(f"✓ Successfully downloaded: {url}")
            except yt_dlp.DownloadError as e:
                failed_downloads += 1
                logging.error(f"✗ Download failed for {url}: {str(e)}")
            except Exception as e:
                failed_downloads += 1
                logging.error(f"✗ Unexpected error for {url}: {str(e)}")
    
    return successful_downloads, failed_downloads

def process_url(url, output_dir):
    """Process a single URL for downloading."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    return download_audio([url], output_dir)

def process_playlist(playlist_url, output_dir):
    """Process a YouTube playlist for downloading."""
    # Extract individual video URLs from the playlist
    logging.info(f"Extracting URLs from playlist: {playlist_url}")
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'ignoreerrors': True,
    }
    
    urls = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        if info and 'entries' in info:
            for entry in info['entries']:
                if entry and 'url' in entry:
                    urls.append(entry['url'])
    
    return download_audio(urls, output_dir)