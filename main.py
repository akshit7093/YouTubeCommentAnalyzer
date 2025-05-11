from flask import Flask, render_template, request, send_file, session
import pyfile_web_scraping
import sentiment_analysis_youtube_comments
import io
from fpdf import FPDF
import pandas as pd
import os
import re
from datetime import datetime
import logging

app = Flask(__name__)
app.secret_key = 'your-secret-key-12345'  # Replace with a secure key in production

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route("/")
def home():
    return render_template('index.html')

@app.route('/scrap', methods=['POST'])
def scrap_comments():
    url = request.form.get('youtube url')
    emailto = request.form.get('user mail id')
    logger.info(f"Received scrape request for URL: {url}, Email: {emailto}")

    # Clear session data to ensure fresh values
    session.pop('video_title', None)
    session.pop('video_owner', None)
    logger.info("Cleared previous session data")

    # Delete old comments file to ensure fresh data
    comments_file_path = "Full Comments.csv"
    if os.path.exists(comments_file_path):
        try:
            os.remove(comments_file_path)
            logger.info(f"Deleted old {comments_file_path}")
        except OSError as e:
            logger.error(f"Failed to delete {comments_file_path}: {e}")
            return render_template('index.html', error_message=f"Error: Could not delete old comments file: {e}")

    # Scrape comments
    try:
        file_and_detail = pyfile_web_scraping.scrapfyt(url)
        logger.info(f"Scraping completed for URL: {url}")
    except Exception as e:
        logger.error(f"Scraping failed for URL {url}: {e}")
        return render_template('index.html', error_message=f"Error: Scraping failed: {e}")

    # Verify comments file was created
    if not os.path.exists(comments_file_path):
        logger.error(f"{comments_file_path} not found after scraping")
        return render_template('index.html', error_message=f"Error: {comments_file_path} not found. Scraping might have failed.")

    # Delete old analysis files to ensure fresh data
    analysis_files = ["analysis_results.txt", "batch_insights.json"]
    for f_path in analysis_files:
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
                logger.info(f"Deleted old {f_path}")
            except OSError as e:
                logger.error(f"Failed to delete {f_path}: {e}")
                # Optionally, decide if this error should halt the process
                # return render_template('index.html', error_message=f"Error: Could not delete old analysis file: {e}")

    # Analyze comments
    try:
        classified_comments, insights, num_good, num_bad, num_normal = sentiment_analysis_youtube_comments.analyze_comments_gemma(comments_file_path)
        logger.info("Comment analysis completed")
    except Exception as e:
        logger.error(f"Comment analysis failed: {e}")
        return render_template('index.html', error_message=f"Error: Comment analysis failed: {e}")

    # Extract video details
    list_file_and_detail = list(file_and_detail)
    if len(list_file_and_detail) > 1:
        video_title, video_owner, video_comment_with_replies, video_comment_without_replies = list_file_and_detail[1:]
    else:
        video_title, video_owner, video_comment_with_replies, video_comment_without_replies = "Unknown", "Unknown", "N/A", "N/A"
        logger.warning("Scraping did not return all expected video details")

    # Store video details in session
    session['video_title'] = video_title
    session['video_owner'] = video_owner
    logger.info(f"Stored in session - video_title: {video_title}, video_owner: {video_owner}")

    after_complete_message = "Comment analysis complete using Gemma model."

    return render_template("index.html", after_complete_message=after_complete_message, title=video_title,
                           owner=video_owner, comment_w_replies=video_comment_with_replies,
                           comment_wo_replies=video_comment_without_replies,
                           insights=insights,
                           num_good=num_good, num_bad=num_bad, num_normal=num_normal,
                           raw_classified_comments=classified_comments)

@app.route('/download_pdf')
def download_pdf():
    def sanitize_text(text):
        """Convert text to string and replace problematic characters for PDF generation."""
        if not isinstance(text, str):
            text = str(text)
        # More aggressive sanitization: encode to ASCII, ignoring errors.
        # This helps ensure compatibility with FPDF's font handling, especially for TrueType fonts.
        return text.encode('ascii', 'ignore').decode('ascii')
        # Replace characters not supported by latin-1.
        # This is often more robust for FPDF's TrueType font handling.
        return text.encode('latin-1', 'replace').decode('latin-1')

    def parse_markdown_line(line):
        """Parse Markdown syntax and return styling instructions."""
        style = {'bold': False, 'italic': False, 'size': 11, 'indent': 0}
        text = line.strip()

        # Handle headers (## Heading)
        if text.startswith('## '):
            style['size'] = 14
            style['bold'] = True
            text = text[3:].strip()
            return text, style

        # Handle bullet points (* or -)
        if text.startswith('* ') or text.startswith('- '):
            style['indent'] = 10
            text = text[2:].strip()
            # Check for sub-bullets
            if text.startswith('* ') or text.startswith('- '):
                style['indent'] = 20
                text = text[2:].strip()

        # Handle bold (**text**)
        bold_pattern = r'\*\*(.*?)\*\*'
        if re.search(bold_pattern, text):
            style['bold'] = True
            text = re.sub(bold_pattern, r'\1', text)

        # Handle italic (*text*)
        italic_pattern = r'\*(.*?)\*'
        if re.search(italic_pattern, text) and not text.startswith('* '):
            style['italic'] = True
            text = re.sub(italic_pattern, r'\1', text)

        # Clean up LaTeX-like artifacts
        text = re.sub(r'\${.*?}\$', '', text)  # Remove ${...}$
        text = text.replace(r'\sim', '~')

        return text, style

    logger.info("Starting PDF generation")

    # Delete old analysis files to ensure fresh data for PDF
    analysis_files_pdf = ["analysis_results.txt", "batch_insights.json"]
    for f_path_pdf in analysis_files_pdf:
        if os.path.exists(f_path_pdf):
            try:
                os.remove(f_path_pdf)
                logger.info(f"Deleted old {f_path_pdf} for PDF generation")
            except OSError as e:
                logger.error(f"Failed to delete {f_path_pdf} for PDF generation: {e}")
                # Optionally, decide if this error should halt the process
                # return f"Error: Could not delete old analysis file for PDF: {e}", 500

    # Re-run analysis
    comments_file_path = "Full Comments.csv"
    if not os.path.exists(comments_file_path):
        logger.error(f"{comments_file_path} not found for PDF generation")
        return "Comments file not found.", 404

    try:
        classified_comments, insights, num_good, num_bad, num_normal = sentiment_analysis_youtube_comments.analyze_comments_gemma(comments_file_path)
        logger.info("Re-ran comment analysis for PDF")
    except Exception as e:
        logger.error(f"Comment analysis failed for PDF: {e}")
        return f"Error: Comment analysis failed: {e}", 500

    # Deduplicate comments based on username and comment text
    seen_comments = set()
    unique_comments = []
    for item in classified_comments:
        comment_key = (item.get('username', 'N/A'), item.get('comment', ''))
        if comment_key not in seen_comments:
            seen_comments.add(comment_key)
            unique_comments.append(item)
    classified_comments = unique_comments
    logger.info(f"Deduplicated comments, total: {len(classified_comments)}")

    # Get video details from session
    video_title = session.get('video_title', 'Unknown')
    video_owner = session.get('video_owner', 'Unknown')
    logger.info(f"Using session data - video_title: {video_title}, video_owner: {video_owner}")

    # Custom FPDF class for headers and footers
    class CustomPDF(FPDF):
        def __init__(self, font_name):
            super().__init__()
            self.font_name = font_name
            self.total_pages = 0

        def header(self):
            # Skip header on cover page (page 1)
            if self.page_no() > 1:
                self.set_font(self.font_name, 'B', 10)
                self.set_y(5)
                self.cell(0, 10, "YouTube Comment Analysis Report", align='C')
                self.ln(10)

        def footer(self):
            # Add page number on all pages
            self.set_y(-15)
            self.set_font(self.font_name, '', 8)
            self.cell(0, 10, f"Page {self.page_no()} of {{total}}", align='C')

        def set_total_pages(self, total):
            self.total_pages = total
            self.alias_nb_pages('{total}')

    # Initialize PDF
    pdf = CustomPDF(font_name='Arial')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=15, top=10, right=15)

    # Font setup
    current_font_name = 'Arial'
    font_path_dejavu = os.path.join(app.root_path, 'DejaVuSans.ttf')

    logger.info(f"Attempting to load DejaVu font from: {font_path_dejavu}")
    if os.path.exists(font_path_dejavu):
        try:
            pdf.add_font('DejaVu', '', font_path_dejavu, uni=True)
            pdf.add_font('DejaVu', 'B', font_path_dejavu, uni=True)
            pdf.add_font('DejaVu', 'I', font_path_dejavu, uni=True)
            current_font_name = 'DejaVu'
            pdf.font_name = 'DejaVu'
            logger.info("Successfully loaded DejaVu font")
        except RuntimeError as e:
            logger.warning(f"Failed to load DejaVu font: {e}. Using Arial")
    else:
        logger.warning(f"DejaVuSans.ttf not found. Using Arial")

    # Cover Page
    pdf.add_page()
    pdf.set_font(current_font_name, 'B', 20)
    pdf.cell(0, 20, "YouTube Comment Analysis Report", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font(current_font_name, '', 14)
    pdf.cell(0, 10, f"Video: {sanitize_text(video_title)}", ln=True, align='C')
    pdf.cell(0, 10, f"Channel: {sanitize_text(video_owner)}", ln=True, align='C')
    pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.ln(20)
    pdf.set_font(current_font_name, '', 12)
    pdf.cell(0, 10, "Generated by Sentiment Analysis Tool", ln=True, align='C')

    # Main Content
    pdf.add_page()
    pdf.set_font(current_font_name, 'B', 16)
    pdf.cell(0, 10, "Analysis Summary", ln=True, align='C')
    pdf.ln(5)

    # Statistics Table
    pdf.set_font(current_font_name, '', 12)

    # Ensure sentiment counts are integers before calculations
    try:
        num_good = int(num_good) if str(num_good).strip() else 0
    except (ValueError, TypeError):
        num_good = 0
    try:
        num_bad = int(num_bad) if str(num_bad).strip() else 0
    except (ValueError, TypeError):
        num_bad = 0
    try:
        num_normal = int(num_normal) if str(num_normal).strip() else 0
    except (ValueError, TypeError):
        num_normal = 0

    total_comments = num_good + num_bad + num_normal
    percentages = {
        'Good': (num_good / total_comments * 100) if total_comments > 0 else 0,
        'Bad': (num_bad / total_comments * 100) if total_comments > 0 else 0,
        'Normal': (num_normal / total_comments * 100) if total_comments > 0 else 0
    }
    pdf.set_fill_color(200, 220, 255)
    pdf.set_line_width(0.5)
    pdf.cell(60, 10, "Category", border=1, fill=True)
    pdf.cell(40, 10, "Count", border=1, fill=True)
    pdf.cell(40, 10, "Percentage", border=1, fill=True)
    pdf.ln()
    pdf.set_fill_color(255, 255, 255)
    for category, count in [('Good', num_good), ('Bad', num_bad), ('Normal', num_normal)]:
        pdf.cell(60, 10, category, border=1)
        pdf.cell(40, 10, str(count), border=1)
        pdf.cell(40, 10, f"{percentages[category]:.1f}%", border=1)
        pdf.ln()
    pdf.ln(10)

    # Insights Section
    pdf.set_font(current_font_name, 'B', 14)
    pdf.cell(0, 10, "Insights", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)

    sanitized_insights = sanitize_text(insights)
    for line in sanitized_insights.split('\n'):
        text, style = parse_markdown_line(line)
        if not text.strip():
            continue
        pdf.set_font(current_font_name, 'B' if style['bold'] else ('I' if style['italic'] else ''), style['size'])
        pdf.set_x(15 + style['indent'])
        try:
            pdf.multi_cell(180 - style['indent'], 8, text, align='L')
        except UnicodeEncodeError:
            encoded_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(180 - style['indent'], 8, encoded_text, align='L')
            logger.warning(f"Replaced non-latin-1 characters in insights: '{text[:30]}...'")
        pdf.ln(2)
    pdf.ln(5)

    # Comments Section
    pdf.set_font(current_font_name, 'B', 14)
    pdf.cell(0, 10, "Comments by Sentiment", ln=True)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)

    # Group comments by tag
    comments_by_tag = {'Good': [], 'Bad': [], 'Normal': []}
    for item in classified_comments:
        tag = item.get('tag', 'unknown').capitalize()
        if tag in comments_by_tag:
            comments_by_tag[tag].append(item)

    tag_colors = {'Good': (0, 128, 0), 'Bad': (255, 0, 0), 'Normal': (0, 0, 255)}
    for tag in ['Good', 'Bad', 'Normal']:
        if not comments_by_tag[tag]:
            continue
        pdf.set_font(current_font_name, 'B', 12)
        pdf.set_text_color(*tag_colors[tag])
        pdf.cell(0, 10, f"{tag} Comments ({len(comments_by_tag[tag])})", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
        pdf.set_font(current_font_name, '', 10)
        for item in comments_by_tag[tag]:
            username = sanitize_text(item.get('username', 'N/A'))
            comment_text = sanitize_text(item.get('comment', ''))
            full_comment = f"@{username}: {comment_text}"
            try:
                pdf.multi_cell(0, 7, full_comment)
            except UnicodeEncodeError:
                encoded_comment = full_comment.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 7, encoded_comment)
                logger.warning(f"Replaced non-latin-1 characters in comment: '{full_comment[:30]}...'")
            pdf.ln(2)
        pdf.ln(5)

    # Set total pages for footer
    pdf.set_total_pages(pdf.page_no())
    logger.info(f"PDF generated with {pdf.page_no()} pages")

    # Output PDF
    pdf_output = io.BytesIO()
    pdf_data = pdf.output(dest='S')
    if isinstance(pdf_data, str):
        pdf_content_as_bytes = pdf_data.encode('latin-1')
    else:
        pdf_content_as_bytes = pdf_data

    pdf_output.write(pdf_content_as_bytes)
    pdf_output.seek(0)

    return send_file(pdf_output, as_attachment=True, download_name="YouTube_Comment_Report.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)  # Enable debug mode for better error reporting