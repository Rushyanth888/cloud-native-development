import os
from flask import Flask, redirect, request
from google.cloud import storage

app = Flask(__name__)
BUCKET_NAME = "rushyanth123"

storage_client = storage.Client()

@app.route('/')
def index():
    index_html = """
    <form method="post" enctype="multipart/form-data" action="/upload">
      <div>
        <label for="file">Choose file to upload</label>
        <input type="file" id="file" name="form_file" accept="image/jpeg"/>
      </div>
      <div>
        <button>Submit</button>
      </div>
    </form>
    <h2>Uploaded Files:</h2>
    <ul>"""

    for file in list_files():
        index_html += f'<li><a href="/files/{file}">{file}</a></li>'

    index_html += "</ul>"
    return index_html

@app.route('/upload', methods=["POST"])
def upload():
    file = request.files['form_file']
    if file:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file.filename)
        blob.upload_from_file(file)
    return redirect("/")

@app.route('/files')
def list_files():
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = bucket.list_blobs()
    files = [blob.name for blob in blobs if blob.name.lower().endswith((".jpeg", ".jpg"))]
    return files

@app.route('/files/<filename>')
def get_file(filename):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    return redirect(blob.public_url)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
