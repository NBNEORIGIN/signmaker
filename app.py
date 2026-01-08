"""SignMaker Web App - Hosted signage product generator."""
import os
import json
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template_string, jsonify, request, Response, send_file
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from config import SECRET_KEY, SIZES, COLORS, BRAND_NAME
from models import init_db, Product
from jobs import submit_job, get_job, get_all_jobs, job_to_dict, start_workers

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialize database on startup
init_db()

# Start background workers
start_workers()

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SignMaker</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 2rem; margin-bottom: 5px; }
        .header p { opacity: 0.9; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .tab {
            padding: 12px 24px;
            background: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.2s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .tab:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
        .tab.active { background: #667eea; color: white; }
        .panel { display: none; }
        .panel.active { display: block; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .card h2 { margin-bottom: 15px; color: #333; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5a6fd6; }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #218838; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-secondary:hover { background: #5a6268; }
        input, select, textarea {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 1rem;
            width: 100%;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
        .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        .status-pending { background: #ffc107; color: #000; }
        .status-approved { background: #28a745; color: white; }
        .status-rejected { background: #dc3545; color: white; }
        .output-box {
            background: #1e1e1e;
            color: #0f0;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .product-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .product-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .product-card img {
            width: 100%;
            height: 200px;
            object-fit: contain;
            background: #f8f9fa;
        }
        .product-card-body { padding: 15px; }
        .product-card h3 { font-size: 1.1rem; margin-bottom: 10px; }
        .product-meta { color: #666; font-size: 0.9rem; }
        .actions { display: flex; gap: 10px; margin-top: 15px; }
        .actions .btn { flex: 1; }
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-info { background: #e7f3ff; color: #0066cc; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🪧 SignMaker</h1>
        <p>Signage Product Generator & Publisher</p>
    </div>
    
    <div class="container">
        <div class="tabs">
            <button class="tab active" onclick="showTab('products')">📦 Products</button>
            <button class="tab" onclick="showTab('qa')">✅ QA Review</button>
            <button class="tab" onclick="showTab('generate')">🎨 Generate</button>
            <button class="tab" onclick="showTab('export')">📤 Export</button>
        </div>
        
        <!-- Products Tab -->
        <div id="products-panel" class="panel active">
            <div class="card">
                <h2>Product List</h2>
                <div style="margin-bottom: 15px;">
                    <button class="btn btn-primary" onclick="showAddProduct()">+ Add Product</button>
                    <button class="btn btn-secondary" onclick="loadProducts()">↻ Refresh</button>
                </div>
                <table id="products-table">
                    <thead>
                        <tr>
                            <th>M Number</th>
                            <th>Description</th>
                            <th>Size</th>
                            <th>Color</th>
                            <th>EAN</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="products-tbody"></tbody>
                </table>
            </div>
        </div>
        
        <!-- QA Review Tab -->
        <div id="qa-panel" class="panel">
            <div class="card">
                <h2>QA Review</h2>
                <button class="btn btn-secondary" onclick="loadQAProducts()">↻ Refresh</button>
                <div id="qa-grid" class="product-grid" style="margin-top: 20px;"></div>
            </div>
        </div>
        
        <!-- Generate Tab -->
        <div id="generate-panel" class="panel">
            <div class="card">
                <h2>Generate Images & Content</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label>Product Theme (for AI)</label>
                        <textarea id="theme" rows="3" placeholder="Describe the sign type..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Target Use Cases</label>
                        <textarea id="use-cases" rows="3" placeholder="Where will this sign be used?"></textarea>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <button class="btn btn-primary" onclick="generateImages()">🎨 Generate Images</button>
                    <button class="btn btn-success" onclick="generateContent()">📝 Generate Content</button>
                    <button class="btn btn-primary" onclick="runFullPipeline()">🚀 Run Full Pipeline</button>
                </div>
                <div id="generate-output" class="output-box" style="margin-top: 20px; display: none;"></div>
            </div>
        </div>
        
        <!-- Export Tab -->
        <div id="export-panel" class="panel">
            <div class="card">
                <h2>Export Flatfile</h2>
                <p style="margin-bottom: 15px; color: #666;">Generate Amazon flatfile for approved products.</p>
                <button class="btn btn-success" onclick="exportFlatfile()">📥 Download Amazon Flatfile</button>
                <div id="export-status" style="margin-top: 15px;"></div>
            </div>
        </div>
    </div>
    
    <!-- Add/Edit Product Modal -->
    <div id="product-modal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000;">
        <div style="background: white; max-width: 600px; margin: 50px auto; border-radius: 12px; padding: 20px;">
            <h2 id="modal-title">Add Product</h2>
            <form id="product-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>M Number</label>
                        <input type="text" id="f-m_number" required placeholder="M1234">
                    </div>
                    <div class="form-group">
                        <label>EAN</label>
                        <input type="text" id="f-ean" placeholder="5056338664471">
                    </div>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <input type="text" id="f-description" required placeholder="Self Adhesive no entry aluminium sign">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Size</label>
                        <select id="f-size">
                            <option value="dracula">Dracula (9.5x9.5cm) - XS</option>
                            <option value="saville">Saville (11x9.5cm) - S</option>
                            <option value="dick">Dick (14x9cm) - M</option>
                            <option value="barzan">Barzan (19x14cm) - L</option>
                            <option value="baby_jesus">Baby Jesus (29x19cm) - XL</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Color</label>
                        <select id="f-color">
                            <option value="silver">Silver</option>
                            <option value="gold">Gold</option>
                            <option value="white">White</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Icon Files</label>
                    <input type="text" id="f-icon_files" placeholder="no_entry.png">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Orientation</label>
                        <select id="f-orientation">
                            <option value="landscape">Landscape</option>
                            <option value="portrait">Portrait</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Mounting Type</label>
                        <select id="f-mounting_type">
                            <option value="self_adhesive">Self Adhesive</option>
                            <option value="pre_drilled">Pre-Drilled</option>
                        </select>
                    </div>
                </div>
                <div style="margin-top: 20px; display: flex; gap: 10px;">
                    <button type="submit" class="btn btn-primary">Save</button>
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        let products = [];
        
        function showTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelector(`[onclick="showTab('${tab}')"]`).classList.add('active');
            document.getElementById(`${tab}-panel`).classList.add('active');
            
            if (tab === 'products') loadProducts();
            if (tab === 'qa') loadQAProducts();
        }
        
        async function loadProducts() {
            const resp = await fetch('/api/products');
            products = await resp.json();
            renderProductsTable();
        }
        
        function renderProductsTable() {
            const tbody = document.getElementById('products-tbody');
            tbody.innerHTML = products.map(p => `
                <tr>
                    <td><strong>${p.m_number}</strong></td>
                    <td>${p.description || ''}</td>
                    <td>${p.size || ''}</td>
                    <td>${p.color || ''}</td>
                    <td style="font-family: monospace;">${String(p.ean || '')}</td>
                    <td><span class="status-badge status-${p.qa_status || 'pending'}">${p.qa_status || 'pending'}</span></td>
                    <td>
                        <button class="btn btn-secondary" onclick="editProduct('${p.m_number}')" style="padding: 5px 10px;">Edit</button>
                        <button class="btn btn-danger" onclick="deleteProduct('${p.m_number}')" style="padding: 5px 10px;">Delete</button>
                    </td>
                </tr>
            `).join('');
        }
        
        async function loadQAProducts() {
            const resp = await fetch('/api/products');
            products = await resp.json();
            renderQAGrid();
        }
        
        function renderQAGrid() {
            const grid = document.getElementById('qa-grid');
            grid.innerHTML = products.map(p => `
                <div class="product-card">
                    <img src="/api/preview/${p.m_number}" alt="${p.m_number}">
                    <div class="product-card-body">
                        <h3>${p.m_number}</h3>
                        <p class="product-meta">${p.description || ''}</p>
                        <p class="product-meta">${p.size} / ${p.color}</p>
                        <div class="actions">
                            <button class="btn btn-success" onclick="setQAStatus('${p.m_number}', 'approved')">✓ Approve</button>
                            <button class="btn btn-danger" onclick="setQAStatus('${p.m_number}', 'rejected')">✗ Reject</button>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        async function setQAStatus(mNumber, status) {
            await fetch(`/api/products/${mNumber}`, {
                method: 'PATCH',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({qa_status: status})
            });
            loadQAProducts();
        }
        
        function showAddProduct() {
            document.getElementById('modal-title').textContent = 'Add Product';
            document.getElementById('product-form').reset();
            document.getElementById('f-m_number').disabled = false;
            document.getElementById('product-modal').style.display = 'block';
        }
        
        function editProduct(mNumber) {
            const p = products.find(x => x.m_number === mNumber);
            if (!p) return;
            document.getElementById('modal-title').textContent = 'Edit Product';
            document.getElementById('f-m_number').value = p.m_number;
            document.getElementById('f-m_number').disabled = true;
            document.getElementById('f-description').value = p.description || '';
            document.getElementById('f-size').value = p.size || 'dracula';
            document.getElementById('f-color').value = p.color || 'silver';
            document.getElementById('f-ean').value = p.ean || '';
            document.getElementById('f-icon_files').value = p.icon_files || '';
            document.getElementById('f-orientation').value = p.orientation || 'landscape';
            document.getElementById('f-mounting_type').value = p.mounting_type || 'self_adhesive';
            document.getElementById('product-modal').style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('product-modal').style.display = 'none';
        }
        
        document.getElementById('product-form').onsubmit = async (e) => {
            e.preventDefault();
            const data = {
                m_number: document.getElementById('f-m_number').value,
                description: document.getElementById('f-description').value,
                size: document.getElementById('f-size').value,
                color: document.getElementById('f-color').value,
                ean: document.getElementById('f-ean').value,
                icon_files: document.getElementById('f-icon_files').value,
                orientation: document.getElementById('f-orientation').value,
                mounting_type: document.getElementById('f-mounting_type').value,
            };
            
            const isEdit = document.getElementById('f-m_number').disabled;
            const url = isEdit ? `/api/products/${data.m_number}` : '/api/products';
            const method = isEdit ? 'PATCH' : 'POST';
            
            await fetch(url, {
                method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            
            closeModal();
            loadProducts();
        };
        
        async function deleteProduct(mNumber) {
            if (!confirm(`Delete ${mNumber}?`)) return;
            await fetch(`/api/products/${mNumber}`, {method: 'DELETE'});
            loadProducts();
        }
        
        async function generateImages() {
            const output = document.getElementById('generate-output');
            output.style.display = 'block';
            output.textContent = 'Starting image generation...\\n';
            
            const resp = await fetch('/api/generate/images', {method: 'POST'});
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                output.textContent += decoder.decode(value);
                output.scrollTop = output.scrollHeight;
            }
        }
        
        async function generateContent() {
            const theme = document.getElementById('theme').value;
            const useCases = document.getElementById('use-cases').value;
            const output = document.getElementById('generate-output');
            output.style.display = 'block';
            output.textContent = 'Starting content generation...\\n';
            
            const resp = await fetch(`/api/generate/content?theme=${encodeURIComponent(theme)}&use_cases=${encodeURIComponent(useCases)}`, {method: 'POST'});
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                output.textContent += decoder.decode(value);
                output.scrollTop = output.scrollHeight;
            }
        }
        
        async function runFullPipeline() {
            const theme = document.getElementById('theme').value;
            const useCases = document.getElementById('use-cases').value;
            const output = document.getElementById('generate-output');
            output.style.display = 'block';
            output.textContent = 'Starting full pipeline...\\n';
            
            const resp = await fetch(`/api/generate/full?theme=${encodeURIComponent(theme)}&use_cases=${encodeURIComponent(useCases)}`, {method: 'POST'});
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                output.textContent += decoder.decode(value);
                output.scrollTop = output.scrollHeight;
            }
        }
        
        async function exportFlatfile() {
            const status = document.getElementById('export-status');
            status.innerHTML = '<div class="alert alert-info">Generating flatfile...</div>';
            
            try {
                const resp = await fetch('/api/export/flatfile', {method: 'POST'});
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `amazon_flatfile_${new Date().toISOString().slice(0,10)}.xlsx`;
                    a.click();
                    status.innerHTML = '<div class="alert alert-success">Flatfile downloaded!</div>';
                } else {
                    status.innerHTML = '<div class="alert alert-error">Failed to generate flatfile</div>';
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        // Load products on page load
        loadProducts();
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(Product.all())


@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.json
    Product.create(data)
    return jsonify({"success": True})


@app.route('/api/products/<m_number>', methods=['GET'])
def get_product(m_number):
    product = Product.get(m_number)
    if product:
        return jsonify(product)
    return jsonify({"error": "Not found"}), 404


@app.route('/api/products/<m_number>', methods=['PATCH'])
def update_product(m_number):
    data = request.json
    Product.update(m_number, data)
    return jsonify({"success": True})


@app.route('/api/products/<m_number>', methods=['DELETE'])
def delete_product(m_number):
    Product.delete(m_number)
    return jsonify({"success": True})


@app.route('/api/preview/<m_number>')
def preview_product(m_number):
    """Generate PNG preview for a product."""
    product = Product.get(m_number)
    if not product:
        return "Not found", 404
    
    try:
        from image_generator import generate_product_image
        png_bytes = generate_product_image(product, "main")
        return Response(png_bytes, mimetype='image/png')
    except Exception as e:
        # Fallback to placeholder SVG on error
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">
            <rect width="300" height="200" fill="#f8d7da"/>
            <text x="150" y="90" text-anchor="middle" font-family="Arial" font-size="16" fill="#721c24">{m_number}</text>
            <text x="150" y="120" text-anchor="middle" font-family="Arial" font-size="12" fill="#721c24">Preview error</text>
            <text x="150" y="145" text-anchor="middle" font-family="Arial" font-size="10" fill="#999">{str(e)[:40]}</text>
        </svg>'''
        return Response(svg, mimetype='image/svg+xml')


@app.route('/api/generate/images', methods=['POST'])
def generate_images():
    """Generate product images for approved products."""
    from image_generator import generate_images_job
    
    products = Product.approved()
    if not products:
        products = Product.all()  # Fall back to all if none approved
    
    if not products:
        return jsonify({"error": "No products to generate"}), 400
    
    job_id = submit_job(
        f"Generate images for {len(products)} products",
        generate_images_job,
        products,
        upload_to_r2=True
    )
    
    return jsonify({"job_id": job_id, "products": len(products)})


@app.route('/api/jobs')
def list_jobs():
    """List all background jobs."""
    jobs = get_all_jobs()
    return jsonify([job_to_dict(j) for j in jobs])


@app.route('/api/jobs/<job_id>')
def get_job_status(job_id):
    """Get status of a specific job."""
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job_to_dict(job))


@app.route('/api/generate/content', methods=['POST'])
def generate_content():
    """Generate AI content for approved products."""
    from content_generator import generate_content_job
    
    theme = request.args.get('theme', '')
    use_cases = request.args.get('use_cases', '')
    
    products = Product.approved()
    if not products:
        products = Product.all()
    
    if not products:
        return jsonify({"error": "No products to generate content for"}), 400
    
    job_id = submit_job(
        f"Generate content for {len(products)} products",
        generate_content_job,
        products,
        theme=theme,
        use_cases=use_cases
    )
    
    return jsonify({"job_id": job_id, "products": len(products)})


@app.route('/api/generate/full', methods=['POST'])
def generate_full():
    """Run full pipeline."""
    def stream():
        yield "Full pipeline not yet implemented in web version.\n"
    return Response(stream(), mimetype='text/plain')


@app.route('/api/export/flatfile', methods=['POST'])
def export_flatfile():
    """Export Amazon flatfile for approved products."""
    from io import BytesIO
    import openpyxl
    
    products = Product.approved()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    
    # Headers
    headers = ['m_number', 'description', 'size', 'color', 'ean', 'qa_status']
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    
    # Data
    for row, p in enumerate(products, 2):
        for col, header in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=p.get(header, ''))
    
    # Save to bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'amazon_flatfile_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
