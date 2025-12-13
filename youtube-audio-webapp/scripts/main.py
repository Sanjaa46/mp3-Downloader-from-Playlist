"""
YouTube Audio Web Application
This script serves as the entry point for the YouTube Audio Downloader web application.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)