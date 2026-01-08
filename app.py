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
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }
        @media (max-width: 1200px) {
            .product-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 800px) {
            .product-grid { grid-template-columns: 1fr; }
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
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 15px;">
                    <button class="btn btn-secondary" onclick="loadQAProducts()">↻ Refresh</button>
                </div>
                <div id="qa-grid" class="product-grid" style="margin-top: 20px;"></div>
            </div>
            <!-- Debug Terminal -->
            <div class="card" style="margin-top: 20px;">
                <h3 style="margin-bottom: 10px;">Debug Console</h3>
                <div id="debug-console" class="output-box" style="height: 150px; font-size: 11px;"></div>
            </div>
        </div>
        
        <!-- Generate Tab -->
        <div id="generate-panel" class="panel">
            <div class="card">
                <h2>Generate Images & Content</h2>
                
                <!-- Step 1: Product Summary -->
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0;">📋 Product Summary</h3>
                    <div id="product-summary" style="font-size: 13px; color: #555;">
                        <em>Loading product summary...</em>
                    </div>
                </div>
                
                <!-- Step 2: Sample Images for AI Context -->
                <div style="background: #f0f7ff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin: 0 0 10px 0;">🖼️ Sample Images for AI Context</h3>
                    <p style="font-size: 12px; color: #666; margin-bottom: 10px;">
                        These images will be sent to the AI to help it understand your product range.
                    </p>
                    <div id="sample-images" style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <em style="color: #888;">Loading sample images...</em>
                    </div>
                </div>
                
                <!-- Step 3: AI Prompt Configuration -->
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
                
                <!-- Step 4: AI System Prompt (editable) -->
                <div class="form-group" style="margin-top: 15px;">
                    <label>AI System Prompt (editable)</label>
                    <textarea id="ai-system-prompt" rows="6" style="font-family: monospace; font-size: 11px;"></textarea>
                    <button class="btn btn-secondary" onclick="resetSystemPrompt()" style="margin-top: 5px; font-size: 11px;">Reset to Default</button>
                </div>
                
                <!-- Action Buttons -->
                <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-secondary" onclick="previewAIPrompt()">👁️ Preview Full Prompt</button>
                    <button class="btn btn-primary" onclick="generateImages()">🎨 Generate Images</button>
                    <button class="btn btn-success" onclick="generateContent()">📝 Generate Content</button>
                    <button class="btn btn-primary" onclick="runFullPipeline()">🚀 Run Full Pipeline</button>
                </div>
                
                <!-- AI Response Preview (editable before applying) -->
                <div id="ai-response-section" style="display: none; margin-top: 20px;">
                    <h3>📝 AI Generated Content (Review & Edit)</h3>
                    <textarea id="ai-response" rows="10" style="font-family: monospace; font-size: 11px; width: 100%;"></textarea>
                    <div style="margin-top: 10px;">
                        <button class="btn btn-success" onclick="applyAIContent()">✓ Apply Content</button>
                        <button class="btn btn-secondary" onclick="discardAIContent()">✗ Discard</button>
                    </div>
                </div>
            </div>
            
            <!-- Debug Terminal -->
            <div class="card" style="margin-top: 20px;">
                <h3 style="margin-bottom: 10px;">Debug Console</h3>
                <div id="generate-debug-console" class="output-box" style="height: 200px; font-size: 11px;"></div>
            </div>
        </div>
        
        <!-- Export Tab -->
        <div id="export-panel" class="panel">
            <div class="card">
                <h2>Export Products</h2>
                <p style="margin-bottom: 15px; color: #666;">Export approved products to various platforms.</p>
                
                <h3 style="margin-top: 20px;">Marketplace Exports</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
                    <button class="btn btn-success" onclick="exportFlatfile()">📥 Amazon Flatfile</button>
                    <button class="btn btn-warning" onclick="exportEtsy()">📥 Etsy Shop Uploader</button>
                </div>
                
                <h3>eBay API Publishing</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 20px;">
                    <button class="btn btn-primary" onclick="publishToEbay(true)">🛒 Publish to eBay (with Ads)</button>
                    <button class="btn btn-secondary" onclick="publishToEbay(false)">🛒 Publish to eBay (no Ads)</button>
                    <span style="color: #888; font-size: 12px;">Creates listings via eBay API with auto-promotion (5% ad rate)</span>
                </div>
                
                <h3>M Number Folders (Staff)</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-success" onclick="exportMNumberFolders()">📁 Download M Number Folders</button>
                </div>
                <p style="margin-top: 10px; color: #888; font-size: 12px;">
                    Full directory structure for Google Drive: 001 Design/001 MASTER FILE (SVG), 002 Images (PNG/JPEG).
                </p>
                
                <h3 style="margin-top: 20px;">AI Lifestyle Images</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                    <button class="btn btn-primary" onclick="generateLifestyleImages()">🎨 Generate Lifestyle Images</button>
                    <span style="color: #888; font-size: 12px;">Uses DALL-E 3 to create contextual product scenes (requires OPENAI_API_KEY)</span>
                </div>
                
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
                        <button class="btn btn-primary" onclick="downloadProductImages('${p.m_number}')" style="padding: 5px 10px;">📦</button>
                        <button class="btn btn-danger" onclick="deleteProduct('${p.m_number}')" style="padding: 5px 10px;">Delete</button>
                    </td>
                </tr>
            `).join('');
        }
        
        // Debug console logging
        function debugLog(message, type = 'info') {
            const console = document.getElementById('debug-console');
            if (!console) return;
            const timestamp = new Date().toLocaleTimeString();
            const color = type === 'error' ? '#f00' : type === 'success' ? '#0f0' : '#0ff';
            console.innerHTML += `<span style="color: ${color}">[${timestamp}] ${message}</span>\n`;
            console.scrollTop = console.scrollHeight;
        }
        
        async function loadQAProducts() {
            debugLog('Loading products...');
            const resp = await fetch('/api/products');
            products = await resp.json();
            debugLog(`Loaded ${products.length} products`, 'success');
            renderQAGrid();
        }
        
        function renderQAGrid() {
            const grid = document.getElementById('qa-grid');
            // Group products by size and description to show variants together
            // Order: saville, dracula first (top row), then baby_jesus, dick (bottom row)
            const sizeOrder = ['saville', 'dracula', 'barzan', 'baby_jesus', 'dick'];
            const silverProducts = products
                .filter(p => p.color === 'silver')
                .sort((a, b) => sizeOrder.indexOf(a.size) - sizeOrder.indexOf(b.size));
            
            grid.innerHTML = silverProducts.map(p => {
                // Find gold and white variants
                const goldVariant = products.find(v => v.size === p.size && v.description === p.description && v.color === 'gold');
                const whiteVariant = products.find(v => v.size === p.size && v.description === p.description && v.color === 'white');
                const showOrientationToggle = p.size === 'dick' || p.size === 'baby_jesus';
                
                return `
                <div class="product-card">
                    <!-- Header with title -->
                    <div style="padding: 10px 15px; background: #667eea; color: white;">
                        <h3 style="margin: 0; font-size: 14px;">${p.description || p.m_number}</h3>
                        <span style="font-size: 11px; opacity: 0.9;">${p.size}${showOrientationToggle ? ` - ${p.orientation || 'landscape'}` : ''}</span>
                    </div>
                    
                    <!-- Large Silver Preview -->
                    <div style="padding: 15px; background: #e8e8e8; text-align: center;">
                        <img id="main-preview-${p.m_number}" src="/api/preview/${p.m_number}?t=${Date.now()}" alt="${p.m_number}" style="max-width: 100%; max-height: 250px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
                        <div style="margin-top: 8px; font-size: 11px;">
                            <strong>${p.m_number}</strong> - Silver
                            <button onclick="setQAStatus('${p.m_number}', 'rejected')" style="font-size: 9px; padding: 2px 6px; margin-left: 6px; cursor: pointer; background: #dc3545; color: white; border: none; border-radius: 3px;">✗ Reject</button>
                        </div>
                    </div>
                    
                    <!-- Controls Section - ABOVE variants -->
                    <div style="padding: 10px; background: #f0f0f0; border-top: 1px solid #ddd;">
                        ${showOrientationToggle ? `
                        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px;">
                            <label style="width: 70px; font-size: 11px;">Orientation:</label>
                            <select id="orientation-${p.m_number}" onchange="updateOrientation('${p.m_number}', this.value)" style="flex: 1; padding: 3px; font-size: 11px;">
                                <option value="landscape" ${(p.orientation || 'landscape') === 'landscape' ? 'selected' : ''}>Landscape</option>
                                <option value="portrait" ${p.orientation === 'portrait' ? 'selected' : ''}>Portrait</option>
                            </select>
                        </div>
                        ` : ''}
                        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 8px;">
                            <label style="width: 70px; font-size: 11px;">Icon Scale:</label>
                            <input type="range" id="icon-scale-${p.m_number}" min="0.5" max="1.5" step="0.01" value="${p.icon_scale || 1.0}" 
                                oninput="updateScaleDisplay('${p.m_number}', this.value)"
                                onchange="updateProductScale('${p.m_number}')"
                                style="flex: 1;">
                            <input type="number" id="icon-scale-input-${p.m_number}" min="0.5" max="1.5" step="0.01" value="${(p.icon_scale || 1.0).toFixed(2)}"
                                onchange="setIconScale('${p.m_number}', this.value)"
                                style="width: 50px; font-size: 10px; padding: 2px;">
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <label style="width: 70px; font-size: 11px;">Position:</label>
                            <div style="display: grid; grid-template-columns: 26px 26px 26px; gap: 2px;">
                                <div></div>
                                <button type="button" onclick="moveIcon('${p.m_number}', 0, -2)" style="padding: 3px 6px; font-size: 9px; cursor: pointer;">▲</button>
                                <div></div>
                                <button type="button" onclick="moveIcon('${p.m_number}', -2, 0)" style="padding: 3px 6px; font-size: 9px; cursor: pointer;">◀</button>
                                <button type="button" onclick="centerIcon('${p.m_number}')" style="padding: 3px 5px; font-size: 7px; cursor: pointer;">⊙</button>
                                <button type="button" onclick="moveIcon('${p.m_number}', 2, 0)" style="padding: 3px 6px; font-size: 9px; cursor: pointer;">▶</button>
                                <div></div>
                                <button type="button" onclick="moveIcon('${p.m_number}', 0, 2)" style="padding: 3px 6px; font-size: 9px; cursor: pointer;">▼</button>
                                <div></div>
                            </div>
                            <span style="font-size: 9px; color: #666;" id="offset-${p.m_number}">(${(p.icon_offset_x || 0).toFixed(0)}, ${(p.icon_offset_y || 0).toFixed(0)})</span>
                            <button class="btn btn-secondary" onclick="regenerateVariants('${p.m_number}')" style="background: #6c757d; padding: 4px 8px; font-size: 10px; margin-left: auto;">🔄 Regenerate</button>
                        </div>
                    </div>
                    
                    <!-- Smaller Gold/White Variants - BELOW controls -->
                    <div style="display: flex; gap: 10px; padding: 10px; background: #f8f8f8; justify-content: center; flex-wrap: wrap;">
                        ${goldVariant ? `
                        <div style="text-align: center;">
                            <img src="/api/preview/${goldVariant.m_number}?t=${Date.now()}" alt="${goldVariant.m_number}" style="width: 80px; height: 80px; object-fit: contain; border-radius: 4px; border: 1px solid #ddd; background: white;">
                            <div style="font-size: 8px; margin-top: 3px;">
                                <strong>${goldVariant.m_number}</strong> Gold
                                <button onclick="setQAStatus('${goldVariant.m_number}', 'rejected')" style="font-size: 7px; padding: 1px 3px; margin-left: 2px; cursor: pointer; background: #dc3545; color: white; border: none; border-radius: 2px;">✗</button>
                            </div>
                        </div>
                        ` : ''}
                        ${whiteVariant ? `
                        <div style="text-align: center;">
                            <img src="/api/preview/${whiteVariant.m_number}?t=${Date.now()}" alt="${whiteVariant.m_number}" style="width: 80px; height: 80px; object-fit: contain; border-radius: 4px; border: 1px solid #ddd; background: white;">
                            <div style="font-size: 8px; margin-top: 3px;">
                                <strong>${whiteVariant.m_number}</strong> White
                                <button onclick="setQAStatus('${whiteVariant.m_number}', 'rejected')" style="font-size: 7px; padding: 1px 3px; margin-left: 2px; cursor: pointer; background: #dc3545; color: white; border: none; border-radius: 2px;">✗</button>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    
                    <!-- Action buttons -->
                    <div style="padding: 10px; background: white; border-top: 1px solid #eee;">
                        <button class="btn btn-success" onclick="approveWithVariants('${p.m_number}')" style="width: 100%;">✓ Approve All Colors</button>
                    </div>
                </div>
            `}).join('');
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
            status.innerHTML = '<div class="alert alert-info">Generating Amazon flatfile...</div>';
            
            try {
                const resp = await fetch('/api/export/flatfile', {method: 'POST'});
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `amazon_flatfile_${new Date().toISOString().slice(0,10)}.xlsx`;
                    a.click();
                    status.innerHTML = '<div class="alert alert-success">Amazon flatfile downloaded!</div>';
                } else {
                    status.innerHTML = '<div class="alert alert-error">Failed to generate flatfile</div>';
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        async function exportEbay() {
            const status = document.getElementById('export-status');
            status.innerHTML = '<div class="alert alert-info">Generating eBay CSV...</div>';
            
            try {
                const resp = await fetch('/api/export/ebay', {method: 'POST'});
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `ebay_listings_${new Date().toISOString().slice(0,10)}.csv`;
                    a.click();
                    status.innerHTML = '<div class="alert alert-success">eBay CSV downloaded!</div>';
                } else {
                    status.innerHTML = '<div class="alert alert-error">Failed to generate eBay CSV</div>';
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        async function exportEtsy() {
            const status = document.getElementById('export-status');
            status.innerHTML = '<div class="alert alert-info">Generating Etsy Shop Uploader...</div>';
            
            try {
                const resp = await fetch('/api/export/etsy', {method: 'POST'});
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `etsy_shop_uploader_${new Date().toISOString().slice(0,10)}.xlsx`;
                    a.click();
                    status.innerHTML = '<div class="alert alert-success">Etsy Shop Uploader downloaded!</div>';
                } else {
                    status.innerHTML = '<div class="alert alert-error">Failed to generate Etsy file</div>';
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        async function exportAllImages() {
            const status = document.getElementById('export-status');
            status.innerHTML = '<div class="alert alert-info">Generating images ZIP... This may take a while.</div>';
            
            try {
                const resp = await fetch('/api/export/images', {method: 'POST'});
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `product_images_${new Date().toISOString().slice(0,10)}.zip`;
                    a.click();
                    status.innerHTML = '<div class="alert alert-success">Images ZIP downloaded!</div>';
                } else {
                    status.innerHTML = '<div class="alert alert-error">Failed to generate images ZIP</div>';
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        async function downloadProductImages(mNumber) {
            window.location.href = `/api/export/images/${mNumber}`;
        }
        
        async function publishToEbay(withAds) {
            const status = document.getElementById('export-status');
            status.innerHTML = '<div class="alert alert-info">Publishing to eBay... This may take a minute.</div>';
            
            try {
                const resp = await fetch(`/api/ebay/publish?promote=${withAds}`, {method: 'POST'});
                const data = await resp.json();
                
                if (data.success) {
                    let msg = `eBay listing created! ${data.products} products published.`;
                    if (data.url) {
                        msg += ` <a href="${data.url}" target="_blank">View on eBay</a>`;
                    }
                    if (data.promoted) {
                        msg += ' (Auto-promoted with 5% ad rate)';
                    }
                    status.innerHTML = `<div class="alert alert-success">${msg}</div>`;
                } else {
                    status.innerHTML = `<div class="alert alert-error">Error: ${data.error}</div>`;
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        async function exportMNumberFolders() {
            const status = document.getElementById('export-status');
            status.innerHTML = '<div class="alert alert-info">Generating M Number folders... This may take a while.</div>';
            
            try {
                const resp = await fetch('/api/export/m-number-folders', {method: 'POST'});
                if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `m_number_folders_${new Date().toISOString().slice(0,10)}.zip`;
                    a.click();
                    status.innerHTML = '<div class="alert alert-success">M Number folders downloaded!</div>';
                } else {
                    status.innerHTML = '<div class="alert alert-error">Failed to generate M Number folders</div>';
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        async function generateLifestyleImages() {
            const status = document.getElementById('export-status');
            status.innerHTML = '<div class="alert alert-info">Generating lifestyle images with DALL-E 3... This may take a few minutes.</div>';
            
            try {
                const resp = await fetch('/api/generate/lifestyle', {method: 'POST'});
                const data = await resp.json();
                
                if (data.success) {
                    status.innerHTML = `<div class="alert alert-success">Generated ${data.generated} lifestyle images! (${data.skipped} skipped, ${data.failed} failed)</div>`;
                } else {
                    status.innerHTML = `<div class="alert alert-error">Error: ${data.error}</div>`;
                }
            } catch (e) {
                status.innerHTML = `<div class="alert alert-error">Error: ${e.message}</div>`;
            }
        }
        
        // Debounce timers for updates
        const updateTimers = {};
        
        function updateScaleDisplay(mNumber, value) {
            document.getElementById(`icon-scale-input-${mNumber}`).value = parseFloat(value).toFixed(2);
        }
        
        function setIconScale(mNumber, value) {
            const scale = parseFloat(value);
            if (scale >= 0.5 && scale <= 1.5) {
                document.getElementById(`icon-scale-${mNumber}`).value = scale;
                updateProductScale(mNumber);
            }
        }
        
        function updateProductScale(mNumber) {
            const iconScale = document.getElementById(`icon-scale-${mNumber}`).value;
            
            // Debounce: wait 300ms after last change before updating
            if (updateTimers[mNumber]) {
                clearTimeout(updateTimers[mNumber]);
            }
            updateTimers[mNumber] = setTimeout(async () => {
                try {
                    const resp = await fetch(`/api/products/${mNumber}/scale`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({icon_scale: parseFloat(iconScale)})
                    });
                    if (resp.ok) {
                        refreshProductImage(mNumber);
                        const p = products.find(x => x.m_number === mNumber);
                        if (p) {
                            p.icon_scale = parseFloat(iconScale);
                        }
                    }
                } catch (e) {
                    console.error('Failed to update scale:', e);
                }
            }, 300);
        }
        
        async function approveWithVariants(mNumber) {
            // Get the silver product's settings
            const silverProduct = products.find(x => x.m_number === mNumber);
            if (!silverProduct) return;
            
            const { icon_scale, icon_offset_x, icon_offset_y, size, description } = silverProduct;
            
            // Find gold and white variants (same size and description)
            const variants = products.filter(p => 
                p.size === size && 
                p.description === description && 
                (p.color === 'gold' || p.color === 'white')
            );
            
            // Apply settings to all variants and approve
            try {
                // Approve silver
                await fetch(`/api/products/${mNumber}`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({qa_status: 'approved'})
                });
                
                // Apply settings to gold/white variants and approve
                for (const variant of variants) {
                    await fetch(`/api/products/${variant.m_number}/scale`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({icon_scale: icon_scale})
                    });
                    await fetch(`/api/products/${variant.m_number}/position`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({icon_offset_x: icon_offset_x || 0, icon_offset_y: icon_offset_y || 0})
                    });
                    await fetch(`/api/products/${variant.m_number}`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({qa_status: 'approved'})
                    });
                }
                
                loadQAProducts();
            } catch (e) {
                console.error('Failed to approve variants:', e);
            }
        }
        
        async function regenerateVariants(mNumber) {
            // Get the silver product's settings
            const silverProduct = products.find(x => x.m_number === mNumber);
            if (!silverProduct) return;
            
            // Show loading state
            const btn = event.target;
            const originalText = btn.innerHTML;
            btn.innerHTML = '⏳ Working...';
            btn.disabled = true;
            debugLog(`Regenerating variants for ${mNumber}...`);
            
            const { icon_scale, icon_offset_x, icon_offset_y, size, description } = silverProduct;
            
            // Find gold and white variants
            const variants = products.filter(p => 
                p.size === size && 
                p.description === description && 
                (p.color === 'gold' || p.color === 'white')
            );
            
            // Apply silver settings to all variants and refresh images
            try {
                for (const variant of variants) {
                    debugLog(`  Updating ${variant.m_number}...`);
                    await fetch(`/api/products/${variant.m_number}/scale`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({icon_scale: icon_scale || 1.0})
                    });
                    await fetch(`/api/products/${variant.m_number}/position`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({icon_offset_x: icon_offset_x || 0, icon_offset_y: icon_offset_y || 0})
                    });
                }
                
                debugLog(`Regenerated ${variants.length + 1} variants`, 'success');
                
                // Refresh all variant images
                refreshProductImage(mNumber);
                for (const variant of variants) {
                    refreshProductImage(variant.m_number);
                }
            } catch (e) {
                debugLog(`Error: ${e.message}`, 'error');
                console.error('Failed to regenerate variants:', e);
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
        
        async function moveIcon(mNumber, dx, dy) {
            const p = products.find(x => x.m_number === mNumber);
            if (!p) return;
            
            const newX = (p.icon_offset_x || 0) + dx;
            const newY = (p.icon_offset_y || 0) + dy;
            
            try {
                const resp = await fetch(`/api/products/${mNumber}/position`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({icon_offset_x: newX, icon_offset_y: newY})
                });
                if (resp.ok) {
                    p.icon_offset_x = newX;
                    p.icon_offset_y = newY;
                    document.getElementById(`offset-${mNumber}`).textContent = `(${newX.toFixed(0)}, ${newY.toFixed(0)})`;
                    refreshProductImage(mNumber);
                }
            } catch (e) {
                console.error('Failed to move icon:', e);
            }
        }
        
        async function centerIcon(mNumber) {
            try {
                const resp = await fetch(`/api/products/${mNumber}/position`, {
                    method: 'PATCH',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({icon_offset_x: 0, icon_offset_y: 0})
                });
                if (resp.ok) {
                    const p = products.find(x => x.m_number === mNumber);
                    if (p) {
                        p.icon_offset_x = 0;
                        p.icon_offset_y = 0;
                    }
                    document.getElementById(`offset-${mNumber}`).textContent = '(0, 0)';
                    refreshProductImage(mNumber);
                }
            } catch (e) {
                console.error('Failed to center icon:', e);
            }
        }
        
        function refreshProductImage(mNumber) {
            const img = document.querySelector(`img[src*="/api/preview/${mNumber}"]`);
            if (img) {
                img.src = `/api/preview/${mNumber}?t=${Date.now()}`;
            }
        }
        
        async function updateOrientation(mNumber, orientation) {
            const silverProduct = products.find(x => x.m_number === mNumber);
            if (!silverProduct) return;
            
            const { size, description } = silverProduct;
            
            // Find all color variants
            const allVariants = products.filter(p => 
                p.size === size && p.description === description
            );
            
            try {
                // Update orientation for all variants
                for (const variant of allVariants) {
                    await fetch(`/api/products/${variant.m_number}`, {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({orientation: orientation})
                    });
                    variant.orientation = orientation;
                }
                
                // Refresh all images
                loadQAProducts();
            } catch (e) {
                console.error('Failed to update orientation:', e);
            }
        }
        
        // ============ GENERATE TAB FUNCTIONS ============
        
        // Debug logging for Generate tab
        function genLog(message, type = 'info') {
            const console = document.getElementById('generate-debug-console');
            if (!console) return;
            const timestamp = new Date().toLocaleTimeString();
            const color = type === 'error' ? '#f00' : type === 'success' ? '#0f0' : '#0ff';
            console.innerHTML += `<span style="color: ${color}">[${timestamp}] ${message}</span>\n`;
            console.scrollTop = console.scrollHeight;
        }
        
        // Default system prompt
        const DEFAULT_SYSTEM_PROMPT = `You are an expert product content writer for Amazon marketplace listings.
You will be provided with:
1. A summary of the product range (sizes, shapes, colors)
2. Sample images showing the actual products
3. Theme and use case information

IMPORTANT: The products come in MULTIPLE sizes and shapes:
- Rectangular signs: saville (115x95mm), dick (140x90mm), barzan (194x143mm), baby_jesus (290x190mm)
- Circular signs: dracula (95mm diameter)
- All signs come in 3 colors: silver, gold, and white

Generate content that accurately describes ALL variants, not just one shape.
Include dimensions in product descriptions.
Write compelling Amazon-style titles and bullet points.`;

        function resetSystemPrompt() {
            document.getElementById('ai-system-prompt').value = DEFAULT_SYSTEM_PROMPT;
            genLog('System prompt reset to default');
        }
        
        // Load product summary and sample images when Generate tab is shown
        function loadGenerateTabData() {
            genLog('Loading product summary...');
            
            // Build product summary
            const sizes = {};
            const colors = new Set();
            const descriptions = new Set();
            
            products.forEach(p => {
                const size = p.size || 'unknown';
                const color = p.color || 'unknown';
                sizes[size] = (sizes[size] || 0) + 1;
                colors.add(color);
                if (p.description) descriptions.add(p.description);
            });
            
            // Size dimensions
            const sizeDims = {
                'saville': '115x95mm (rectangular)',
                'dick': '140x90mm (rectangular)',
                'barzan': '194x143mm (rectangular)',
                'dracula': '95mm diameter (circular)',
                'baby_jesus': '290x190mm (rectangular)'
            };
            
            let summaryHTML = `<strong>Total Products:</strong> ${products.length}<br>`;
            summaryHTML += `<strong>Colors:</strong> ${Array.from(colors).join(', ')}<br>`;
            summaryHTML += `<strong>Sizes:</strong><br>`;
            for (const [size, count] of Object.entries(sizes)) {
                const dims = sizeDims[size] || 'unknown dimensions';
                summaryHTML += `&nbsp;&nbsp;• ${size}: ${count} products - ${dims}<br>`;
            }
            summaryHTML += `<strong>Product Types:</strong> ${descriptions.size} unique designs`;
            
            document.getElementById('product-summary').innerHTML = summaryHTML;
            genLog(`Found ${products.length} products across ${Object.keys(sizes).length} sizes`, 'success');
            
            // Load sample images - one of each size (silver only for variety)
            const sampleImages = [];
            const seenSizes = new Set();
            
            for (const p of products) {
                if (p.color === 'silver' && !seenSizes.has(p.size)) {
                    sampleImages.push(p);
                    seenSizes.add(p.size);
                }
                if (sampleImages.length >= 5) break;
            }
            
            let imagesHTML = '';
            for (const p of sampleImages) {
                imagesHTML += `
                    <div style="text-align: center;">
                        <img src="/api/preview/${p.m_number}?t=${Date.now()}" 
                             style="width: 100px; height: 80px; object-fit: contain; border: 1px solid #ddd; border-radius: 4px; background: white;">
                        <div style="font-size: 10px; color: #666;">${p.size}</div>
                    </div>
                `;
            }
            
            if (imagesHTML) {
                document.getElementById('sample-images').innerHTML = imagesHTML;
                genLog(`Loaded ${sampleImages.length} sample images for AI context`, 'success');
            } else {
                document.getElementById('sample-images').innerHTML = '<em style="color: #888;">No products available</em>';
            }
            
            // Set default system prompt if empty
            const promptField = document.getElementById('ai-system-prompt');
            if (!promptField.value) {
                promptField.value = DEFAULT_SYSTEM_PROMPT;
            }
        }
        
        function previewAIPrompt() {
            const theme = document.getElementById('theme').value || '(not specified)';
            const useCases = document.getElementById('use-cases').value || '(not specified)';
            const systemPrompt = document.getElementById('ai-system-prompt').value;
            const summary = document.getElementById('product-summary').innerText;
            
            const fullPrompt = `=== SYSTEM PROMPT ===
${systemPrompt}

=== PRODUCT SUMMARY ===
${summary}

=== USER INPUT ===
Theme: ${theme}
Use Cases: ${useCases}

=== SAMPLE IMAGES ===
[${document.querySelectorAll('#sample-images img').length} images will be attached]`;
            
            alert(fullPrompt);
            genLog('Previewed full AI prompt');
        }
        
        async function generateContent() {
            genLog('Starting content generation...');
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '⏳ Generating...';
            
            try {
                const theme = document.getElementById('theme').value;
                const useCases = document.getElementById('use-cases').value;
                const systemPrompt = document.getElementById('ai-system-prompt').value;
                
                // Get sample image M numbers
                const sampleMNumbers = Array.from(document.querySelectorAll('#sample-images img'))
                    .map(img => {
                        const match = img.src.match(/\/api\/preview\/([^?]+)/);
                        return match ? match[1] : null;
                    })
                    .filter(Boolean);
                
                genLog(`Sending ${sampleMNumbers.length} sample images to AI...`);
                
                const resp = await fetch('/api/generate/content', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        theme,
                        use_cases: useCases,
                        system_prompt: systemPrompt,
                        sample_m_numbers: sampleMNumbers
                    })
                });
                
                const data = await resp.json();
                
                if (data.success) {
                    genLog('Content generated successfully!', 'success');
                    document.getElementById('ai-response').value = data.content;
                    document.getElementById('ai-response-section').style.display = 'block';
                } else {
                    genLog(`Error: ${data.error}`, 'error');
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                genLog(`Error: ${e.message}`, 'error');
                console.error('Failed to generate content:', e);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '📝 Generate Content';
            }
        }
        
        function applyAIContent() {
            const content = document.getElementById('ai-response').value;
            genLog('Applying AI content...');
            // TODO: Parse and apply content to products
            alert('Content applied! (Implementation pending)');
            document.getElementById('ai-response-section').style.display = 'none';
        }
        
        function discardAIContent() {
            document.getElementById('ai-response-section').style.display = 'none';
            genLog('AI content discarded');
        }
        
        async function generateImages() {
            genLog('Starting image generation...');
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '⏳ Generating...';
            
            try {
                const resp = await fetch('/api/generate/images', {method: 'POST'});
                const data = await resp.json();
                
                if (data.success) {
                    genLog(`Generated images for ${data.count} products`, 'success');
                    alert(`Generated images for ${data.count} products`);
                } else {
                    genLog(`Error: ${data.error}`, 'error');
                    alert('Error: ' + data.error);
                }
            } catch (e) {
                genLog(`Error: ${e.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🎨 Generate Images';
            }
        }
        
        async function runFullPipeline() {
            genLog('Starting full pipeline...');
            await generateImages();
            await generateContent();
            genLog('Full pipeline complete', 'success');
        }
        
        // Override showTab to load Generate tab data
        const originalShowTab = showTab;
        showTab = function(tabName) {
            originalShowTab(tabName);
            if (tabName === 'generate') {
                loadGenerateTabData();
            }
        };
        
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
    """Generate AI content for products using OpenAI GPT-4 with sample images."""
    import os
    import base64
    import logging
    from image_generator import generate_product_image
    
    data = request.json or {}
    theme = data.get('theme', '')
    use_cases = data.get('use_cases', '')
    system_prompt = data.get('system_prompt', '')
    sample_m_numbers = data.get('sample_m_numbers', [])
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"success": False, "error": "OPENAI_API_KEY not set"}), 400
    
    all_products = Product.all()
    if not all_products:
        return jsonify({"success": False, "error": "No products found"}), 400
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Build product summary
        sizes = {}
        colors = set()
        descriptions = set()
        
        for p in all_products:
            size = p.get('size', 'unknown')
            color = p.get('color', 'unknown')
            sizes[size] = sizes.get(size, 0) + 1
            colors.add(color)
            if p.get('description'):
                descriptions.add(p['description'])
        
        size_dims = {
            'saville': '115x95mm (rectangular)',
            'dick': '140x90mm (rectangular)', 
            'barzan': '194x143mm (rectangular)',
            'dracula': '95mm diameter (circular)',
            'baby_jesus': '290x190mm (rectangular)'
        }
        
        summary = f"Total Products: {len(all_products)}\n"
        summary += f"Colors: {', '.join(colors)}\n"
        summary += "Sizes:\n"
        for size, count in sizes.items():
            dims = size_dims.get(size, 'unknown dimensions')
            summary += f"  - {size}: {count} products - {dims}\n"
        summary += f"Product Types: {len(descriptions)} unique designs"
        
        # Build message content with images for GPT-4 Vision
        content = []
        
        # Add sample images
        for m_number in sample_m_numbers[:5]:  # Limit to 5 images
            product = Product.get(m_number)
            if product:
                try:
                    png_bytes = generate_product_image(product, "main")
                    img_base64 = base64.b64encode(png_bytes).decode()
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }
                    })
                    logging.info(f"Added sample image for {m_number}")
                except Exception as e:
                    logging.warning(f"Failed to generate sample image for {m_number}: {e}")
        
        # Add text prompt
        user_prompt = f"""=== PRODUCT SUMMARY ===
{summary}

=== USER INPUT ===
Theme: {theme or '(not specified)'}
Use Cases: {use_cases or '(not specified)'}

Please generate Amazon marketplace content for these products. Include:
1. Product titles (under 200 characters)
2. 5 bullet points per product
3. Product descriptions

Remember: These products come in MULTIPLE sizes and shapes as shown in the images and summary above."""

        content.append({"type": "text", "text": user_prompt})
        
        # Call OpenAI GPT-4 Vision API
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt or "You are an expert product content writer for Amazon marketplace listings."},
                {"role": "user", "content": content}
            ]
        )
        
        generated_content = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "content": generated_content
        })
        
    except Exception as e:
        logging.error(f"Failed to generate content: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/generate/full', methods=['POST'])
def generate_full():
    """Run full pipeline."""
    def stream():
        yield "Full pipeline not yet implemented in web version.\n"
    return Response(stream(), mimetype='text/plain')


@app.route('/api/ebay/publish', methods=['POST'])
def publish_to_ebay():
    """Publish approved products to eBay via API with auto-promotion."""
    from ebay_api import create_ebay_listing, load_policy_ids
    
    promote = request.args.get('promote', 'true').lower() == 'true'
    ad_rate = request.args.get('ad_rate', '5.0')
    dry_run = request.args.get('dry_run', 'false').lower() == 'true'
    
    products = Product.approved()
    if not products:
        products = Product.all()
    
    if not products:
        return jsonify({"error": "No products to publish"}), 400
    
    try:
        policy_ids = load_policy_ids()
    except FileNotFoundError as e:
        return jsonify({"error": str(e), "hint": "Run ebay_setup_policies.py first"}), 400
    
    try:
        listing_id = create_ebay_listing(
            products=products,
            policy_ids=policy_ids,
            promote=promote,
            ad_rate=ad_rate,
            dry_run=dry_run,
        )
        
        if listing_id:
            result = {
                "success": True,
                "listing_id": listing_id,
                "products": len(products),
                "promoted": promote and listing_id != "DRY_RUN",
            }
            if listing_id != "DRY_RUN":
                result["url"] = f"https://www.ebay.co.uk/itm/{listing_id}"
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to create listing"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/flatfile', methods=['POST'])
def export_flatfile():
    """Export Amazon flatfile for approved products."""
    from io import BytesIO
    import openpyxl
    
    products = Product.approved()
    if not products:
        products = Product.all()
    
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


@app.route('/api/export/ebay', methods=['POST'])
def export_ebay():
    """Export eBay File Exchange CSV."""
    from export_ebay import generate_ebay_csv
    from config import R2_PUBLIC_URL
    
    products = Product.approved()
    if not products:
        products = Product.all()
    
    csv_content = generate_ebay_csv(products, R2_PUBLIC_URL)
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=ebay_listings_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'}
    )


@app.route('/api/export/etsy', methods=['POST'])
def export_etsy():
    """Export Etsy Shop Uploader XLSX."""
    from export_etsy import generate_etsy_xlsx
    from config import R2_PUBLIC_URL
    from io import BytesIO
    
    products = Product.approved()
    if not products:
        products = Product.all()
    
    xlsx_bytes = generate_etsy_xlsx(products, R2_PUBLIC_URL)
    
    return send_file(
        BytesIO(xlsx_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'etsy_shop_uploader_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    )


@app.route('/api/export/images/<m_number>', methods=['GET'])
def export_product_images(m_number):
    """Download all images for a single product as ZIP."""
    from export_images import generate_single_product_zip
    from io import BytesIO
    
    product = Product.get(m_number)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    zip_bytes = generate_single_product_zip(product)
    
    return send_file(
        BytesIO(zip_bytes),
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{m_number}_images.zip'
    )


@app.route('/api/export/images', methods=['POST'])
def export_all_images():
    """Download all product images as ZIP (approved products)."""
    from export_images import generate_images_zip
    from io import BytesIO
    
    products = Product.approved()
    if not products:
        products = Product.all()
    
    if not products:
        return jsonify({"error": "No products to export"}), 400
    
    zip_bytes = generate_images_zip(products)
    
    return send_file(
        BytesIO(zip_bytes),
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'product_images_{datetime.now().strftime("%Y%m%d_%H%M")}.zip'
    )


@app.route('/api/export/m-number-folders/<m_number>', methods=['GET'])
def export_m_number_folder(m_number):
    """Download M Number folder with full structure for staff (single product)."""
    from export_images import generate_single_m_number_folder_zip
    from io import BytesIO
    
    product = Product.get(m_number)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    zip_bytes = generate_single_m_number_folder_zip(product)
    
    return send_file(
        BytesIO(zip_bytes),
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{m_number}_folder.zip'
    )


@app.route('/api/export/m-number-folders', methods=['POST'])
def export_all_m_number_folders():
    """Download all M Number folders with full structure for staff."""
    from export_images import generate_m_number_folder_zip
    from io import BytesIO
    
    products = Product.approved()
    if not products:
        products = Product.all()
    
    if not products:
        return jsonify({"error": "No products to export"}), 400
    
    zip_bytes = generate_m_number_folder_zip(products)
    
    return send_file(
        BytesIO(zip_bytes),
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'm_number_folders_{datetime.now().strftime("%Y%m%d_%H%M")}.zip'
    )


@app.route('/api/products/<m_number>/scale', methods=['PATCH'])
def update_product_scale(m_number):
    """Update icon_scale and text_scale for a product (QA tuning)."""
    data = request.json
    
    product = Product.get(m_number)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    updates = {}
    if 'icon_scale' in data:
        updates['icon_scale'] = float(data['icon_scale'])
    if 'text_scale' in data:
        updates['text_scale'] = float(data['text_scale'])
    
    if updates:
        Product.update(m_number, updates)
    
    return jsonify({"success": True, "updates": updates})


@app.route('/api/products/<m_number>/position', methods=['PATCH'])
def update_product_position(m_number):
    """Update icon_offset_x and icon_offset_y for a product (QA positioning)."""
    data = request.json
    
    product = Product.get(m_number)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    
    updates = {}
    if 'icon_offset_x' in data:
        updates['icon_offset_x'] = float(data['icon_offset_x'])
    if 'icon_offset_y' in data:
        updates['icon_offset_y'] = float(data['icon_offset_y'])
    
    if updates:
        Product.update(m_number, updates)
    
    return jsonify({"success": True, "updates": updates})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
