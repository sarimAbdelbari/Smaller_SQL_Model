from flask import Flask, request, jsonify, render_template, send_from_directory
import os
from werkzeug.utils import secure_filename
from model_loader import model
from query_generator import QueryProcessor
import logging

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create query processor
query_processor = QueryProcessor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle SQL file upload"""
    if 'sqlFile' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['sqlFile']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'sql':
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Set up temporary database from the SQL file
        if not query_processor.setup_temp_db(file_path):
            return jsonify({'error': 'Failed to process SQL file'}), 500
        
        # Parse the SQL file to extract schema
        schema_context = query_processor.parse_sql_file(file_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': file_path,
            'schema': schema_context
        })
    
    return jsonify({'error': 'Invalid file type. Please upload a .sql file'}), 400

@app.route('/generate-query', methods=['POST'])
def generate_query():
    """Generate SQL query from natural language question"""
    if not model.is_loaded():
        return jsonify({'error': 'Model not loaded. Please set a valid model path.'}), 503
        
    data = request.json
    if not data or 'question' not in data or 'schema' not in data:
        return jsonify({'error': 'Missing question or schema'}), 400
    
    question = data['question']
    schema_context = data['schema']
    
    # Generate SQL query using the model
    sql_query = model.generate_sql(question, schema_context)
    print("sql_query&&&&&&&&&&&&&&&&&&", sql_query)
    
    return jsonify({
        'generated_sql': sql_query
    })



@app.route('/set-model-path', methods=['POST'])
def set_model_path():
    """Set local model path"""
    data = request.json
    if not data or 'model_path' not in data:
        return jsonify({'error': 'Missing model path'}), 400
    
    model_path = data['model_path']
    try:
        success = model.set_model_path(model_path)
        if success:
            logger.info(f'Successfully loaded model from: {model_path}')
            return jsonify({'success': True, 'message': f'Model path set to: {model_path}'})
        else:
            logger.error(f'Failed to load model from: {model_path}')
            return jsonify({'error': f'Failed to load model from path: {model_path}'}), 400
    except Exception as e:
        logger.error(f'Error loading model: {str(e)}')
        return jsonify({'error': f'Error loading model: {str(e)}'}), 500

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Clean up resources"""
    query_processor.cleanup()
    return jsonify({'success': True})

if __name__ == '__main__':
    # Try to load the model on startup
    model_loaded = False
    try:
        # First try loading from local models directory
        local_model_path = os.path.join(os.path.dirname(__file__), "models", "sql-model")
        if os.path.exists(local_model_path):
            logger.info('Found model at local path, attempting to load...')
            try:
                import psutil
                available_ram = psutil.virtual_memory().available / (1024 * 1024 * 1024)  # GB
                logger.info(f'Available RAM: {available_ram:.2f} GB')
                
                if available_ram < 8:  # Changed from 16 to 8 GB
                    logger.error('Insufficient RAM available. This model requires at least 8GB of free RAM')
                    logger.error('Consider using a smaller model or increasing available memory')
                    raise MemoryError('Insufficient RAM')
                
                if model.load_model(local_model_path):
                    logger.info(f'Successfully loaded model from local path: {local_model_path}')
                    model_loaded = True
                else:
                    logger.error('Failed to load model from local directory')
            except MemoryError as me:
                logger.error(f'Memory error while loading model: {str(me)}')
            except Exception as e:
                logger.error(f'Error loading model: {str(e)}')
        else:
            logger.warning(f'Local model not found at: {local_model_path}')
            logger.info('Please run download_model.py first to download the model')
    except Exception as e:
        logger.error(f'Startup error: {str(e)}')
    
    if not model_loaded:
        logger.warning('Application starting without model loaded - /generate-query endpoint will return 503')
    
    # Start Flask app without loading model if there were issues
    app.run(debug=True, host='0.0.0.0', port=5000)