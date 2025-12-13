# YouTube Audio Web Application

This project is a web application that allows users to download audio from YouTube videos and playlists. It is built using Flask and provides a user-friendly interface for downloading MP3 audio files.

## Features

- Download audio from individual YouTube videos or playlists.
- User-friendly web interface.
- Supports multiple audio formats.
- Error handling and logging for download processes.

## Project Structure

```
youtube-audio-webapp
├── app
│   ├── __init__.py          # Initializes the Flask application
│   ├── routes.py            # Defines the application routes
│   ├── downloader.py         # Core functionality for downloading audio
│   ├── utils.py             # Utility functions for logging and error handling
│   ├── templates
│   │   └── index.html       # Main HTML template for the web application
│   └── static
│       ├── css
│       │   └── styles.css    # CSS styles for the web application
│       └── js
│           └── app.js        # JavaScript code for client-side interactions
├── scripts
│   └── main.py              # Original script for downloading audio
├── requirements.txt         # Lists project dependencies
├── Dockerfile               # Instructions for building a Docker image
├── .env.example             # Example environment variables
├── .gitignore               # Specifies files to ignore in Git
└── README.md                # Documentation for the project
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd youtube-audio-webapp
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables by copying `.env.example` to `.env` and modifying as needed.

## Usage

1. Run the application:
   ```
   flask run
   ```

2. Open your web browser and navigate to `http://127.0.0.1:5000`.

3. Enter the YouTube video or playlist URL and click the download button.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.