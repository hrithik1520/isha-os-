from flask import Flask, render_template, request, jsonify, send_from_directory
from dataclasses import dataclass, field
import time
import json

app = Flask(__name__, template_folder='../templates', static_folder='../static', static_url_path='/static')

# Document model
@dataclass
class Document:
    doc_type: str
    name: str
    content: str = ""
    created_at: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: str(int(time.time() * 1000)))

    def to_dict(self):
        return {
            'id': self.id,
            'doc_type': self.doc_type,
            'name': self.name,
            'content': self.content,
            'created_at': self.created_at
        }

# Global state
class DesktopState:
    def __init__(self):
        self.clipboard = ""
        self.documents = []
        self.wastebasket = []
        self.stationery = [
            {"label": "Write pad", "type": "write"},
            {"label": "Calc pad", "type": "calc"},
            {"label": "Draw pad", "type": "draw"},
        ]

desktop = DesktopState()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('../static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/desktop')
def get_desktop():
    return jsonify({
        'documents': [d.to_dict() for d in desktop.documents],
        'wastebasket': [d.to_dict() for d in desktop.wastebasket],
        'stationery': desktop.stationery,
        'clipboard': desktop.clipboard
    })

@app.route('/api/document/create', methods=['POST'])
def create_document():
    data = request.json
    doc = Document(
        doc_type=data.get('doc_type'),
        name=data.get('name'),
        content=""
    )
    desktop.documents.append(doc)
    return jsonify(doc.to_dict())

@app.route('/api/document/<doc_id>', methods=['GET'])
def get_document(doc_id):
    for doc in desktop.documents:
        if doc.id == doc_id:
            return jsonify(doc.to_dict())
    return jsonify({'error': 'Document not found'}), 404

@app.route('/api/document/<doc_id>', methods=['PUT'])
def update_document(doc_id):
    data = request.json
    for doc in desktop.documents:
        if doc.id == doc_id:
            doc.content = data.get('content', doc.content)
            doc.name = data.get('name', doc.name)
            return jsonify(doc.to_dict())
    return jsonify({'error': 'Document not found'}), 404

@app.route('/api/document/<doc_id>/delete', methods=['POST'])
def delete_document(doc_id):
    for i, doc in enumerate(desktop.documents):
        if doc.id == doc_id:
            deleted_doc = desktop.documents.pop(i)
            desktop.wastebasket.append(deleted_doc)
            return jsonify({'success': True})
    return jsonify({'error': 'Document not found'}), 404

@app.route('/api/wastebasket/restore/<doc_id>', methods=['POST'])
def restore_document(doc_id):
    for i, doc in enumerate(desktop.wastebasket):
        if doc.id == doc_id:
            restored_doc = desktop.wastebasket.pop(i)
            desktop.documents.append(restored_doc)
            return jsonify({'success': True})
    return jsonify({'error': 'Document not found'}), 404

@app.route('/api/clipboard', methods=['GET'])
def get_clipboard():
    return jsonify({'content': desktop.clipboard})

@app.route('/api/clipboard', methods=['PUT'])
def update_clipboard():
    data = request.json
    desktop.clipboard = data.get('content', '')
    return jsonify({'success': True})
