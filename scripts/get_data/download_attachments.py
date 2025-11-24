import os
import re
import time
import logging
import requests
import pandas as pd
from urllib.parse import unquote

# Configure logging
logging.basicConfig(filename='download_log.txt', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
ATTACHMENTS_DIR = os.path.join(DATA_DIR, 'attachments')
SCHOLARSHIPS_FILE = os.path.join(DATA_DIR, 'scholarships.csv')

def parse_attachments(attachments_string):
    """
    Parses the attachment string to extract file names and URLs.
    """
    attachments = []
    if not isinstance(attachments_string, str):
        return attachments

    parts = attachments_string.split('|')
    for part in parts:
        match = re.search(r'(.+?)\s*\[(https?://.+?)\]', part)
        if match:
            name = match.group(1).strip()
            url = match.group(2).strip()
            attachments.append({'name': name, 'url': url})
    return attachments

def get_file_extension(response):
    """
    Determines the file extension from the Content-Type header or magic number.
    """
    content_type = response.headers.get('Content-Type')
    if content_type:
        import mimetypes
        extension = mimetypes.guess_extension(content_type.split(';')[0])
        if extension:
            return extension

    # If Content-Type is not reliable, use python-magic
    try:
        import magic
        mime = magic.Magic(mime=True)
        content_type = mime.from_buffer(response.content)
        import mimetypes
        extension = mimetypes.guess_extension(content_type)
        if extension:
            return extension
    except ImportError:
        logging.warning("python-magic is not installed. Falling back to URL parsing for file extension.")
    except Exception as e:
        logging.error(f"Error using python-magic: {e}")

    # Fallback to URL parsing
    from urllib.parse import urlparse
    from os.path import splitext
    parsed_url = urlparse(response.url)
    _, extension = splitext(parsed_url.path)
    return extension if extension else '.bin' # Default to .bin if no extension found

def sanitize_filename(name):
    """
    Removes illegal characters from a string so it can be a valid filename.
    """
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def download_attachments(scholarship_id, attachments):
    """
    Downloads attachments for a given scholarship.
    """
    for i, attachment in enumerate(attachments):
        url = attachment['url']
        name = attachment['name']
        try:
            # Insecure: Skipping SSL verification. Use only if you trust the source.
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()

            extension = get_file_extension(response)
            
            # Sanitize the original attachment name to create a valid filename
            sanitized_name = sanitize_filename(name)
            
            # Create a descriptive and unique filename
            filename = f"{scholarship_id}_{sanitized_name}{extension}"
            filepath = os.path.join(ATTACHMENTS_DIR, filename)

            with open(filepath, 'wb') as f:
                f.write(response.content)

            logging.info(f"Successfully downloaded {url} to {filepath} for scholarship {scholarship_id}")
            print(f"Successfully downloaded {url} to {filepath} for scholarship {scholarship_id}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download {url} for scholarship {scholarship_id}: {e}")
            print(f"Failed to download {url} for scholarship {scholarship_id}: {e}")
        
        time.sleep(1) # Be polite to the server

def main():
    """
    Main function to read scholarship data and download attachments.
    """
    if not os.path.exists(SCHOLARSHIPS_FILE):
        logging.error(f"Scholarships file not found at {SCHOLARSHIPS_FILE}")
        print(f"Scholarships file not found at {SCHOLARSHIPS_FILE}")
        return

    df = pd.read_csv(SCHOLARSHIPS_FILE)
    
    # The column with attachment strings is named '附加檔案'
    url_column = '附加檔案'
    if url_column not in df.columns:
        logging.error(f"Column '{url_column}' not found in the CSV file.")
        print(f"Column '{url_column}' not found in the CSV file.")
        return


    for index, row in df.iterrows():
        scholarship_id = row.get('ID', index) # Use 'ID' column if it exists, otherwise use index
        attachments_string = row[url_column]
        attachments = parse_attachments(attachments_string)
        if attachments:
            download_attachments(scholarship_id, attachments)

if __name__ == "__main__":
    main()
