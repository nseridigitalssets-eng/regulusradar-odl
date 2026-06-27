import os
import tempfile
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "opendataloader"})

@app.route('/parse-pdf', methods=['POST'])
def parse_pdf():
    data = request.get_json()

    required = ['job_id', 'niche', 'source', 'pdf_url']
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    pdf_url = data['pdf_url']

    # Gate: reject PDFs over 5MB
    try:
        head = requests.head(pdf_url, timeout=10, allow_redirects=True)
        content_length = int(head.headers.get('content-length', 0))
        if content_length > 5 * 1024 * 1024:
            return jsonify({
                "job_id": data['job_id'],
                "status": "deferred",
                "reason": "PDF exceeds 5MB free tier limit",
                "pdf_url": pdf_url
            }), 200
    except Exception:
        pass

    # Download PDF
    try:
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Failed to fetch PDF: {str(e)}"}), 500

    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    os.unlink(tmp_path)

    # Return metadata — Docling handles actual extraction
    return jsonify({
        "job_id": data['job_id'],
        "status": "fetched",
        "niche": data['niche'],
        "source": data['source'],
        "document_type": data.get('document_type', 'regulatory_pdf'),
        "pdf_url": pdf_url,
        "fetched_at": data.get('fetched_at', ''),
        "title": data.get('title', ''),
        "published_date": data.get('published_date', '')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
