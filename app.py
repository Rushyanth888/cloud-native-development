from flask import Flask, render_template, request, redirect, url_for, Response
from google.cloud import storage
import os
import io
import base64  # Import for Base64 encoding

app = Flask(__name__)

# Google Cloud Storage bucket name
BUCKET_NAME = 'cloudnativeprojectbuck110098'

# Local folder for temporary uploads
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the Google Cloud Storage bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

def list_blobs(bucket_name):
    """Lists all files in the Google Cloud Storage bucket."""
    storage_client = storage.Client()
    return storage_client.list_blobs(bucket_name)

def download_blob_into_memory(bucket_name, blob_name):
    """Downloads a file from Google Cloud Storage into memory."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    file_obj = io.BytesIO()
    blob.download_to_file(file_obj)
    file_obj.seek(0)
    return file_obj.read()

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Handles file upload."""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return redirect(request.url)

        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        upload_blob(BUCKET_NAME, filepath, filename)

        return redirect(url_for('gallery'))
    
    return render_template('upload.html')

@app.route('/gallery')
def gallery():
    """Displays all uploaded images in the gallery."""
    blobs = list_blobs(BUCKET_NAME)
    image_data = {}

    for blob in blobs:
        image_bytes = download_blob_into_memory(BUCKET_NAME, blob.name)
        image_data[blob.name] = base64.b64encode(image_bytes).decode('utf-8')  # Convert to Base64

    return render_template('gallery.html', image_data=image_data)

@app.route('/images/<filename>')
def serve_image(filename):
    """Serves an image directly from Google Cloud Storage."""
    image_bytes = download_blob_into_memory(BUCKET_NAME, filename)
    return Response(image_bytes, mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(debug=True)