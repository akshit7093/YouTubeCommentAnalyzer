i# YouTube Comment Scraper & Sentiment Analyzer

This project is a Python-based application designed to scrape comments from YouTube videos, perform sentiment analysis on these comments, and generate insightful reports. It helps users understand audience reception, identify key themes, and gauge overall sentiment related to YouTube content.

## Key Features

*   **YouTube Comment Scraping**: Fetches comments from a specified YouTube video URL.
*   **Sentiment Analysis**: Analyzes the sentiment of each comment (Positive, Negative, Neutral).
*   **Batch Insights Generation**: Processes comments in batches to provide summarized insights.
*   **Data Export**: Saves scraped comments and analysis results to CSV and text files.
*   **Report Generation**: (Potentially) Generates PDF reports summarizing the findings (based on user's initial description, though not explicitly verified in current file views).
*   **Web Interface**: Provides a simple web interface to input YouTube video URLs and view results.

## Technology Stack

*   **Backend**: Python
    *   Flask (for the web interface - inferred from `templates/index.html`)
    *   Google API Client Library for Python (for YouTube Data API V3)
    *   NLTK (Natural Language Toolkit) for sentiment analysis (inferred from `nltk.txt` and common practice)
    *   Pandas (for data manipulation - common for CSV handling)
    *   FPDF/ReportLab (or similar, if PDF generation is implemented)
*   **Frontend**: HTML, CSS (as seen in `templates/index.html` and `static/style.css`)
*   **Environment**: `.env` file for API key management

## Setup Instructions

### Prerequisites

*   Python 3.x installed (check with `python --version`)
*   pip (Python package installer, usually comes with Python)
*   A Google API Key with YouTube Data API v3 enabled. You can obtain one from the [Google Cloud Console](https://console.cloud.google.com/).

### 1. Clone the Repository

```bash
git clone <repository-url> # Replace <repository-url> with the actual URL
cd YoutubeCommentScrapingandAnalysis
```

### 2. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

*   **Windows**:

    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
*   **macOS/Linux**:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

### 3. Install Dependencies

Install the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

If `nltk` resources are needed (e.g., 'vader_lexicon' for sentiment analysis), you might need to download them. This is often done within the Python script on first run or can be done manually:

```python
import nltk
nltk.download('vader_lexicon')
nltk.download('punkt') # If sentence tokenization is used
```

### 4. Configure API Key

Create a `.env` file in the root directory of the project (`YoutubeCommentScrapingandAnalysis/.env`) and add your Google API Key:

```env
GOOGLE_API_KEY=YOUR_API_KEY_HERE
```

Replace `YOUR_API_KEY_HERE` with your actual Google API Key.

## How to Run the Application

Once the setup is complete, you can run the main application script:

```bash
python main.py
```

This will typically start a local web server (e.g., on `http://127.0.0.1:5000/` if Flask is used with default settings). Open this URL in your web browser to use the application.

## How to Use

1.  Navigate to the application's URL in your web browser.
2.  You should see an input field to enter a YouTube video URL.
3.  Paste the full URL of the YouTube video you want to analyze.
4.  Submit the URL.
5.  The application will scrape the comments, perform sentiment analysis, and display the results. 
6.  Generated files like `comments.csv`, `analysis_results.txt`, and `batch_insights.json` will be saved in the project directory.

## Project Structure

Here's a brief overview of the key files and directories:

```
YoutubeCommentScrapingandAnalysis/
├── .env                    # For API keys and environment variables (needs to be created)
├── Full Comments.csv       # CSV output of all scraped comments
├── README.md               # This file
├── __pycache__/            # Python bytecode cache
├── analysis_results.txt    # Text file with detailed sentiment analysis results
├── batch_insights.json     # JSON file with summarized insights from comment batches
├── comments.csv            # Another CSV output, potentially a subset or processed version
├── delete_files_after_mail.py # Script to delete files after emailing
├── mail_sending_to_user_with_attached_csv_files.py # Script for sending emails with attachments
├── main.py                 # Main application script, likely runs the Flask app
├── nltk.txt                # Potentially NLTK data or related notes
├── pyfile_web_scraping.py  # Core logic for YouTube comment scraping
├── requirements.txt        # Python package dependencies
├── runtime.txt             # Specifies Python runtime for deployment (e.g., Heroku)
├── sentiment_analysis_youtube_comments.py # Core logic for sentiment analysis
├── static/
│   └── style.css           # CSS styles for the web interface
└── templates/
    └── index.html          # HTML template for the web interface
```

## Contributing

(Optional: Add guidelines for contributing if this is an open-source project.)

## License

(Optional: Specify the license for the project, e.g., MIT License. A `license` file exists, so its content should be reflected here or referred to.)
Refer to the <mcfile name="license" path="c:\Users\Akshit\OneDrive\Documents\code\comments\YoutubeCommentScrapingandAnalysis\license"></mcfile> file for licensing information.
