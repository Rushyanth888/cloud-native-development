import os
import json
import io
import logging
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from google.cloud import storage
import google.generativeai as genai

# Initialize Flask app
app = Flask(__name__)

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Get Google Cloud Storage bucket name from environment variable
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
if not BUCKET_NAME:
    logging.error("❌ GCS_BUCKET_NAME environment variable not set.")
    raise ValueError("GCS_BUCKET_NAME environment variable not set.")

# Check and configure Gemini API
api_key = os.getenv("GEMINI_API")
if not api_key:
    logging.error("❌ GEMINI_API environment variable not set.")
    raise ValueError("GEMINI_API environment variable not set.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize Google Cloud Storage Client
storage_client = storage.Client()

# Function to upload a file to Google Cloud Storage
def upload_blob(bucket_name, file_obj, destination_blob_name):
    try:
        logging.info(f"🚀 Uploading {destination_blob_name} to {bucket_name}...")
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_file(file_obj, content_type='image/jpeg')
        logging.info(f"✅ File {destination_blob_name} uploaded successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to upload file: {e}")

# Function to download a file from Google Cloud Storage
def download_blob(bucket_name, filename):
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        if not blob.exists():
            logging.warning(f"⚠️ File {filename} not found in bucket {bucket_name}.")
            return None
        return blob.download_as_bytes()
    except Exception as e:
        logging.error(f"❌ Error retrieving file {filename}: {e}")
        return None

# Function to generate image description using Gemini AI
def generate_image_description(image_bytes):
    try:
        logging.info("📸 Generating image description using Gemini AI...")
        # Upload image to Gemini API
        image_file = genai.upload_file(io.BytesIO(image_bytes), mime_type="image/jpeg")
        
        # Provide a prompt to the AI to generate title and description
        prompt = "Generate a concise title and detailed description for this image. Respond strictly in JSON format with keys 'title' and 'description'."
        
        # Call Gemini API to generate content (description)
        response = model.generate_content([image_file, prompt])
        
        # Ensure valid JSON parsing
        start_index = response.text.find('{')
        end_index = response.text.rfind('}')
        
        if start_index != -1 and end_index != -1:
            json_response = response.text[start_index:end_index+1]
            metadata = json.loads(json_response)
            logging.info(f"✅ Description generated: {metadata}")
            return metadata
        else:
            raise ValueError("No valid JSON found in the response.")
    except Exception as e:
        logging.error(f"❌ Failed to generate description: {e}")
        return {"title": "N/A", "description": "Failed to generate description."}

# Route to fetch an image by filename and serve it
@app.route('/image/<filename>')
def get_image(filename):
    content = download_blob(BUCKET_NAME, filename)
    if content:
        return send_file(io.BytesIO(content), mimetype="image/jpeg")  # Adjust mimetype based on file type
    return jsonify({"error": "Image not found"}), 404

# Route to fetch JSON metadata by filename
@app.route('/metadata/<filename>')
def get_metadata(filename):
    json_filename = f"{os.path.splitext(filename)[0]}.json"
    content = download_blob(BUCKET_NAME, json_filename)
    if content:
        try:
            return jsonify(json.loads(content.decode("utf-8")))
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format"}), 500
    return jsonify({"error": "Metadata not found"}), 404

# Route to list all images
@app.route('/list-images')
def list_images():
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs()
        filenames = [blob.name for blob in blobs if blob.name.lower().endswith(('.png', '.jpg', '.jpeg'))]
        return jsonify(filenames)
    except Exception as e:
        logging.error(f"❌ Failed to list images: {e}")
        return jsonify([])

# Route to upload and process images
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'image' not in request.files:
            logging.warning("⚠️ No file part in request.")
            return redirect(request.url)
        
        image = request.files['image']
        if image.filename == '':
            logging.warning("⚠️ No selected file.")
            return redirect(request.url)

        try:
            image_bytes = image.read()
            if not image_bytes:
                logging.warning("⚠️ Empty file uploaded.")
                return redirect(request.url)

            # Upload directly to GCS
            upload_blob(BUCKET_NAME, io.BytesIO(image_bytes), image.filename)

            # Generate image description using Gemini AI
            metadata = generate_image_description(image_bytes)
            
            # Save JSON metadata in the bucket
            json_blob_name = f"{os.path.splitext(image.filename)[0]}.json"
            upload_blob(BUCKET_NAME, io.BytesIO(json.dumps(metadata).encode()), json_blob_name)

        except Exception as e:
            logging.error(f"❌ Error during processing: {e}")

        return redirect(url_for('index'))

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)

