import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
import re
import json

# Load environment variables from .env file
load_dotenv()

# Configure the Gemma API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please add it.")
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the Generative Model (e.g., 'gemma-2b' or other suitable model)
# Note: Model availability might vary. Check Google AI documentation for current models.
# For text generation tasks, a model like 'gemini-pro' might be more suitable if 'gemma' specific model is not directly available for this type of generation or if it's part of Gemini family.
# Assuming 'gemini-pro' as a placeholder if a direct 'gemma' model for this task isn't specified or easily usable via this SDK path.
# If a specific Gemma model endpoint is required, the SDK usage might differ.
model = genai.GenerativeModel('gemma-3-27b-it') # Or a specific Gemma model if available and preferred

MAX_RETRIES = 3
RETRY_DELAY = 5 # seconds

def classify_comment_batch(comments):
    """Classifies a batch of comments using Gemma API."""
    if not comments:
        return []

    num_comments = len(comments)
    
    # Refined prompt for clarity and strictness
    prompt_parts = [
        f"You are a precise sentiment classification model. Your task is to classify {num_comments} YouTube comments provided below.",
        f"For EACH of the {num_comments} comments, you MUST output ONLY one of the following classifications: 'good', 'bad', or 'normal'.",
        f"Each classification MUST be on a new line. You MUST return exactly {num_comments} lines in total.",
        "Do NOT include any other text, explanations, or numbering. Only the classification words ('good', 'bad', 'normal'), each on its own line."
    ]

    # Add comments to the prompt
    for i, comment_text in enumerate(comments):
        cleaned_comment = " ".join(comment_text.strip().split())[:500] # Keep cleaning and length limit
        prompt_parts.append(f"Comment {i+1}: {cleaned_comment}")
    
    prompt_parts.append("\nClassifications (one per line):") # Clear signal for the model
    prompt = "\n".join(prompt_parts)

    # Ensure the number of classifications matches the number of comments
    expected_classifications = len(comments)

    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            # Ensure response.text exists and is not empty
            if response.text:
                # Split the response by newlines, as we expect one tag per line.
                # Strip whitespace from each line and filter out empty lines.
                lines = [line.strip() for line in response.text.split('\n') if line.strip()]
                
                processed_classifications = []
                valid_tags_set = {'good', 'bad', 'normal'}

                for line in lines:
                    # Find all occurrences of valid tags on the line.
                    # This handles cases where the API might put multiple tags on one line,
                    # or embed them with other text, despite the prompt asking for one tag per line.
                    found_tags_on_line = re.findall(r'\b(good|bad|normal)\b', line, re.IGNORECASE)
                    for tag in found_tags_on_line:
                        processed_classifications.append(tag.lower()) # Ensure consistent casing

                # Handle cases where the number of extracted tags doesn't match the expected number.
                if len(processed_classifications) == expected_classifications:
                    return processed_classifications
                elif len(processed_classifications) > expected_classifications:
                    print(f"Warning: Received {len(processed_classifications)} valid classifications, expected {expected_classifications}. Truncating to the first {expected_classifications}.")
                    return processed_classifications[:expected_classifications]
                else: # len(processed_classifications) < expected_classifications
                    # This case means fewer tags were successfully parsed than expected.
                    # This could be due to API not returning enough lines, or lines not matching the regex.
                    num_missing = expected_classifications - len(processed_classifications)
                    print(f"Warning: Received {len(processed_classifications)} valid classifications, expected {expected_classifications}. Padding with {num_missing} 'normal' value(s).")
                    print(f"Original API response text for debugging: {response.text}") # Log the problematic response
                    processed_classifications.extend(['normal'] * num_missing)
                    return processed_classifications

                # This block is for the case where the initial split and regex found nothing, but response.text was not empty.
                # This is a fallback if the line-by-line parsing above yields no results despite a non-empty response.
                if not processed_classifications and response.text and response.text.strip(): # Ensure response.text is not None before strip()
                    print(f"Warning: Could not parse any valid tags from API response using line-by-line method: '{response.text.strip()}'. Defaulting to 'normal' for all {expected_classifications} comments.")
                    return ['normal'] * expected_classifications
            else:
                print(f"Attempt {attempt + 1}: Received empty response from API. Defaulting to 'normal' for all comments in batch.")
                if attempt == MAX_RETRIES - 1:
                    return ['normal'] * expected_classifications # Fallback
        except Exception as e:
            print(f"Error classifying comments (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                # Fallback if all retries fail
                print("All retries failed for comment classification. Defaulting to 'normal' for all comments in batch.")
                return ['normal'] * expected_classifications
    # This line should ideally not be reached if the loop logic is correct
    print("Exited classification retry loop unexpectedly. Defaulting to 'normal' for all comments in batch.")
    return ['normal'] * expected_classifications

def generate_insights(all_comments_text):
    """Generates insights from all comments using Gemma API."""
    if not all_comments_text:
        return "No comments provided to generate insights."

    prompt = f"""
    As an expert YouTube comment analyst, provide a detailed and structured analysis of the following YouTube comments. 
    For each category below, offer specific insights, and if possible, quote or paraphrase example comments (without revealing usernames) to support your analysis.

    **Detailed Analysis Categories:**

    **1. Overall Video/Post Performance:**
       - General reception (e.g., overwhelmingly positive, mixed, negative).
       - Key indicators of engagement (e.g., active discussions, questions, expressions of learning/enjoyment).
       - Any surprising or unexpected feedback patterns.

    **2. Creator and Content Style Perception:**
       - How is the creator perceived? (e.g., knowledgeable, approachable, entertaining, clear/unclear communicator).
       - What are the common descriptors used for the content style? (e.g., well-explained, thorough, fast-paced, engaging).
       - Does the creator's style resonate well with the audience? Provide evidence.

    **3. Specific Aspects Disliked or Criticized:**
       - Identify recurring themes of criticism (e.g., pacing, clarity on specific topics, technical issues, content choices).
       - Are there any constructive criticisms that offer actionable feedback for the creator?
       - Note any misunderstandings or points of confusion expressed by viewers.

    **4. Specific Aspects Liked or Praised:**
       - Highlight the most frequently praised elements (e.g., specific explanations, examples used, overall value, creator's personality).
       - What do viewers find most helpful or impactful?
       - Are there particular segments or topics that received exceptionally positive feedback?

    **5. Viewer Desires and Suggestions for Future Content:**
       - What are the most common requests for future videos or topics?
       - Are there suggestions for different content formats (e.g., tutorials, live sessions, Q&A)?
       - What unmet needs or interests are viewers expressing?

    **6. Sentiment Breakdown (Summary):**
       - Briefly summarize the proportion of positive, negative, and neutral comments if discernible from the overall tone.

    **Input Comments:**
    ---BEGIN COMMENTS---
    {all_comments_text}
    ---END COMMENTS---

    **Output Format:**
    Please structure your response clearly, using markdown for headings and bullet points for readability. Be comprehensive yet concise.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            if response.text:
                return response.text.strip()
            else:
                print(f"Attempt {attempt + 1}: Received empty response for insights generation.")
                if attempt == MAX_RETRIES - 1:
                    return "Could not generate insights after multiple attempts due to empty API response."
        except Exception as e:
            print(f"Error generating insights (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return f"Failed to generate insights after multiple retries: {e}"
    return "Failed to generate insights after multiple retries."

def extract_batch_insights(batch_comments_text):
    """Extracts key pointers for each insight category from a batch of comments."""
    if not batch_comments_text:
        return {}
    prompt = f"""
    As an expert YouTube comment analyst, for the following batch of YouTube comments, extract key pointers for each of these categories:
    1. Overall Video/Post Performance
    2. Creator and Content Style Perception
    3. Specific Aspects Disliked or Criticized
    4. Specific Aspects Liked or Praised
    5. Viewer Desires and Suggestions for Future Content
    6. Sentiment Breakdown (Summary)
    For each category, provide concise bullet points (max 2-3 per category) summarizing the main insights from this batch. Use JSON format as output, with each category as a key and a list of pointers as the value.
    ---BEGIN COMMENTS---\n{chr(10).join(batch_comments_text)}\n---END COMMENTS---
    Output only the JSON object.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            if response.text:
                # Try to extract JSON from the response
                import json
                try:
                    # Find the first and last curly braces to extract JSON
                    start = response.text.find('{')
                    end = response.text.rfind('}') + 1
                    json_str = response.text[start:end]
                    return json.loads(json_str)
                except Exception as e:
                    print(f"Failed to parse batch insight JSON: {e}\nRaw response: {response.text}")
                    if attempt == MAX_RETRIES - 1:
                        return {}
            else:
                print(f"Attempt {attempt + 1}: Empty response for batch insight extraction.")
                if attempt == MAX_RETRIES - 1:
                    return {}
        except Exception as e:
            print(f"Error extracting batch insights (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return {}
    return {}

def analyze_comments_gemma(comment_file, batch_size=10):
    """Analyzes comments from a CSV file using Gemma API."""
    try:
        dataset = pd.read_csv(comment_file, encoding_errors='ignore')
        if 'Comment' not in dataset.columns:
            raise ValueError("CSV file must contain a 'Comment' column.")
        # Ensure 'Username' column exists, or create a default one
        if 'Username' not in dataset.columns:
            dataset['Username'] = [f"User{i+1}" for i in range(len(dataset))]
            print("Warning: 'Username' column not found. Added default usernames.")
        comments_with_users = list(zip(dataset['Username'].astype(str), dataset['Comment'].astype(str)))
    except FileNotFoundError:
        return [], "Error: Comment file not found.", "", "", ""
    except pd.errors.EmptyDataError:
        return [], "Error: Comment file is empty.", "", "", ""
    except Exception as e:
        return [], f"Error reading CSV: {e}", "", "", ""

    all_classified_comments = []
    all_comments_for_insights = []
    batch_insights_list = []

    for i in range(0, len(comments_with_users), batch_size):
        batch_with_users = comments_with_users[i:i + batch_size]
        batch_comments_text = [comment for _, comment in batch_with_users]
        print(f"Processing batch {i//batch_size + 1}...")
        classifications = classify_comment_batch(batch_comments_text)
        for (username, comment_text), tag in zip(batch_with_users, classifications):
            all_classified_comments.append({"username": username, "comment": comment_text, "tag": tag})
            all_comments_for_insights.append(comment_text)
        # Extract batch insights and append to list
        batch_insights = extract_batch_insights(batch_comments_text)
        batch_insights_list.append(batch_insights)
        time.sleep(1) # Add a small delay to avoid hitting API rate limits too quickly

    # Append batch insights to JSON file
    with open('batch_insights.json', 'a') as json_file:
        json.dump(batch_insights_list, json_file)
        json_file.write('\n')

    # Generate overall insights from all comments
    # Join all comments into a single string for the generate_insights function
    all_comments_text_for_insights = "\n".join(all_comments_for_insights)
    insights = generate_insights(all_comments_text_for_insights)
    
    # Write insights and comments to a text file
    with open('analysis_results.txt', 'w', encoding='utf-8') as text_file:
        text_file.write('Insights:\n')
        text_file.write(str(insights) + '\n\n') # Ensure insights is a string
        text_file.write('All Comments:\n')
        for item in all_classified_comments:
            text_file.write(f"[{item['tag'].capitalize()}] {item['username']}: {item['comment']}\n")

    # Calculate counts of good, bad, and normal comments
    num_good = sum(1 for item in all_classified_comments if item['tag'] == 'good')
    num_bad = sum(1 for item in all_classified_comments if item['tag'] == 'bad')
    num_normal = sum(1 for item in all_classified_comments if item['tag'] == 'normal')

    return all_classified_comments, insights, num_good, num_bad, num_normal

if __name__ == '__main__':
    # Example usage:
    # Create a dummy comments.csv for testing
    dummy_data = {
        'Username': ['user1', 'user2', 'user3', 'user4', 'user5'],
        'Comment': [
            'This was an amazing video, learned a lot!', 
            'I did not like this at all, very confusing.', 
            'It was okay, not great but not terrible.',
            'Great content, please make more like this!',
            'This is the worst explanation ever.'
            ]
    }
    df_dummy = pd.DataFrame(dummy_data)
    df_dummy.to_csv("comments.csv", index=False)

    print("Starting analysis...")
    classified_comments, insights_text, num_good, num_bad, num_normal = analyze_comments_gemma("comments.csv", batch_size=2)
    
    print("\n--- Classified Comments ---")
    for item in classified_comments:
        print(f"User: {item['username']}, Tag: {item['tag']}, Comment: {item['comment'][:50]}...")
    
    print(f"\nGood: {num_good}, Bad: {num_bad}, Normal: {num_normal}")
    
    print("\n--- Generated Insights ---")
    print(insights_text)

    # Clean up dummy file
    # os.remove("comments.csv")
