"""
YouTube Audio Downloader
Downloads MP3 audio from YouTube videos or playlists.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import yt_dlp


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('youtube_downloader.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def is_playlist_url(url):
    """Check if the URL is a YouTube playlist."""
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
        return 'list=' in parsed_url.query
    return False


def read_urls_from_file(file_path):
    """Read URLs from a text file."""
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    urls.append(line)
        return urls
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading file {file_path}: {str(e)}")


def create_output_directory(output_dir):
    """Create output directory if it doesn't exist."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)


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
        'ignoreerrors': True,  # Continue on errors
        'no_warnings': False,
        'extractaudio': True,
        'audioformat': 'mp3',
        'embed_subs': False,
        'writesubtitles': False,
    }


def download_audio(urls, output_dir, logger):
    """Download audio from YouTube URLs."""
    create_output_directory(output_dir)
    
    ydl_opts = get_ydl_opts(output_dir)
    successful_downloads = 0
    failed_downloads = 0
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, url in enumerate(urls, 1):
            try:
                logger.info(f"Processing ({i}/{len(urls)}): {url}")
                
                # Extract info first to get title
                info = ydl.extract_info(url, download=False)
                if info:
                    title = info.get('title', 'Unknown Title')
                    logger.info(f"Title: {title}")
                
                # Download the audio
                ydl.download([url])
                successful_downloads += 1
                logger.info(f"✓ Successfully downloaded: {title}")
                
            except yt_dlp.DownloadError as e:
                failed_downloads += 1
                logger.error(f"✗ Download failed for {url}: {str(e)}")
            except Exception as e:
                failed_downloads += 1
                logger.error(f"✗ Unexpected error for {url}: {str(e)}")
    
    # Summary
    logger.info(f"\n=== Download Summary ===")
    logger.info(f"Successful downloads: {successful_downloads}")
    logger.info(f"Failed downloads: {failed_downloads}")
    logger.info(f"Total processed: {len(urls)}")
    logger.info(f"Output directory: {os.path.abspath(output_dir)}")


def extract_playlist_urls(playlist_url, logger):
    """Extract individual video URLs from a playlist."""
    logger.info(f"Extracting URLs from playlist: {playlist_url}")
    
    ydl_opts = {
        'quiet': False,  # Enable output for debugging
        'no_warnings': False,
        'extract_flat': True,  # Only extract URLs, don't download
        'ignoreerrors': True,
    }
    
    urls = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Attempting to extract playlist information...")
            info = ydl.extract_info(playlist_url, download=False)
            
            if info:
                logger.info(f"Playlist info extracted. Type: {info.get('_type', 'unknown')}")
                logger.info(f"Playlist title: {info.get('title', 'Unknown')}")
                
                # Check if it's a playlist
                if info.get('_type') == 'playlist' and 'entries' in info:
                    logger.info(f"Processing playlist with {len(info['entries'])} entries")
                    for i, entry in enumerate(info['entries']):
                        if entry is None:
                            logger.warning(f"Entry {i} is None (possibly deleted/private video)")
                            continue
                            
                        video_id = entry.get('id')
                        video_url = entry.get('url')
                        video_title = entry.get('title', 'Unknown Title')
                        
                        if video_url:
                            urls.append(video_url)
                            logger.info(f"  [{i+1}] {video_title}")
                        elif video_id:
                            constructed_url = f"https://www.youtube.com/watch?v={video_id}"
                            urls.append(constructed_url)
                            logger.info(f"  [{i+1}] {video_title} (constructed URL)")
                        else:
                            logger.warning(f"  [{i+1}] Could not extract URL for: {video_title}")
                
                # Handle case where it's a single video with playlist parameter
                elif info.get('_type') in ['video', None] and info.get('id'):
                    logger.info("URL appears to be a single video, not a playlist")
                    video_url = f"https://www.youtube.com/watch?v={info['id']}"
                    urls.append(video_url)
                    logger.info(f"Added single video: {info.get('title', 'Unknown Title')}")
                
                else:
                    logger.error(f"Unexpected info type: {info.get('_type')}")
                    logger.error(f"Available keys: {list(info.keys())}")
            else:
                logger.error("No information extracted from URL")
        
        logger.info(f"Found {len(urls)} videos in playlist")
        return urls
        
    except Exception as e:
        logger.error(f"Error extracting playlist URLs: {str(e)}")
        # Try alternative approach - treat as single video
        logger.info("Attempting to treat as single video...")
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                if info and info.get('id'):
                    single_url = f"https://www.youtube.com/watch?v={info['id']}"
                    logger.info(f"Treating as single video: {info.get('title', 'Unknown')}")
                    return [single_url]
        except Exception as e2:
            logger.error(f"Alternative approach also failed: {str(e2)}")
        
        raise Exception(f"Error extracting playlist URLs: {str(e)}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Download MP3 audio from YouTube videos or playlists',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python youtube_audio_downloader.py -f urls.txt -o ./downloads
  python youtube_audio_downloader.py -p "https://www.youtube.com/playlist?list=PLxxxxxx" -o ./music
  python youtube_audio_downloader.py -u "https://www.youtube.com/watch?v=xxxxxx" -o ./audio
        '''
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--file', 
                           help='Text file containing YouTube URLs (one per line)')
    input_group.add_argument('-p', '--playlist', 
                           help='YouTube playlist URL')
    input_group.add_argument('-u', '--url', 
                           help='Single YouTube video URL')
    
    # Output directory
    parser.add_argument('-o', '--output', 
                       default='./downloads',
                       help='Output directory for MP3 files (default: ./downloads)')
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging()
    logger.info("YouTube Audio Downloader started")
    
    try:
        urls = []
        
        # Determine input source and collect URLs
        if args.file:
            logger.info(f"Reading URLs from file: {args.file}")
            urls = read_urls_from_file(args.file)
        elif args.playlist:
            logger.info(f"Processing playlist: {args.playlist}")
            urls = extract_playlist_urls(args.playlist, logger)
            
            # If playlist extraction failed, try different approaches
            if not urls:
                logger.info("Trying alternative playlist extraction methods...")
                
                # Method 1: Try removing extra parameters
                if '&list=' in args.playlist:
                    clean_playlist_url = args.playlist.split('&list=')[1].split('&')[0]
                    clean_url = f"https://www.youtube.com/playlist?list={clean_playlist_url}"
                    logger.info(f"Trying clean playlist URL: {clean_url}")
                    try:
                        urls = extract_playlist_urls(clean_url, logger)
                    except Exception as e:
                        logger.warning(f"Clean URL approach failed: {e}")
                
                # Method 2: Try with different yt-dlp options
                if not urls:
                    logger.info("Trying with different extraction options...")
                    try:
                        ydl_opts_alt = {
                            'quiet': False,
                            'extract_flat': False,  # Try full extraction
                            'playlistend': 50,  # Limit to first 50 videos
                        }
                        with yt_dlp.YoutubeDL(ydl_opts_alt) as ydl:
                            info = ydl.extract_info(args.playlist, download=False)
                            if info and info.get('entries'):
                                for entry in info['entries']:
                                    if entry and entry.get('webpage_url'):
                                        urls.append(entry['webpage_url'])
                                    elif entry and entry.get('id'):
                                        urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
                                logger.info(f"Alternative method found {len(urls)} videos")
                    except Exception as e:
                        logger.warning(f"Alternative extraction failed: {e}")
        elif args.url:
            logger.info(f"Processing single URL: {args.url}")
            urls = [args.url]
        
        if not urls:
            logger.error("No URLs found to process")
            sys.exit(1)
        
        logger.info(f"Total URLs to process: {len(urls)}")
        
        # Download audio files
        download_audio(urls, args.output, logger)
        
        logger.info("YouTube Audio Downloader completed")
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
