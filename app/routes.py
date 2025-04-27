from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from urllib.parse import urlparse
from app import db
from app.models import User, Question, Statistics, TextChunk
from app.forms import LoginForm, ChangePasswordForm, ChangeApiKeyForm
import json
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import ChangePasswordForm
import sys
import os
from dotenv import load_dotenv, set_key
from pathlib import Path
from datetime import datetime
import logging
import PyPDF2
import tempfile
from werkzeug.utils import secure_filename

# Importar usando caminho relativo
from .openai_client import generate_questions, generate_questions_with_specialized_models
from .database.db_manager import DatabaseManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adicionar o diretório src ao PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Carregar variáveis de ambiente
load_dotenv()

# Criar blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('main.login'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos', 'error')
            logger.warning(f"Falha no login para usuário: {form.username.data}")
            return redirect(url_for('main.login'))
            
        login_user(user, remember=form.remember_me.data)
        logger.info(f"Login bem-sucedido para usuário: {form.username.data}")
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
        
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@main.route('/api/questions', methods=['GET'])
@login_required
def get_questions():
    questions = Question.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': q.id,
        'content': q.content,
        'answer': q.answer,
        'domain': q.domain,
        'process_group': q.process_group,
        'created_at': q.created_at.isoformat()
    } for q in questions])

@main.route('/api/questions', methods=['POST'])
@login_required
def create_question():
    data = request.get_json()
    question = Question(
        content=data['content'],
        answer=data['answer'],
        domain=data['domain'],
        process_group=data['process_group'],
        user_id=current_user.id
    )
    db.session.add(question)
    db.session.commit()
    return jsonify({'message': 'Question created successfully'}), 201

@main.route('/api/statistics', methods=['GET'])
@login_required
def get_statistics():
    stats = Statistics.query.filter_by(user_id=current_user.id).first()
    if not stats:
        stats = Statistics(user_id=current_user.id)
        db.session.add(stats)
        db.session.commit()
    return jsonify({
        'total_questions': stats.total_questions,
        'correct_answers': stats.correct_answers,
        'incorrect_answers': stats.incorrect_answers,
        'last_updated': stats.last_updated.isoformat()
    })

@main.route('/api/generate', methods=['POST'])
@login_required
def generate():
    logger.info("Received generate request")
    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400

        # Validate required fields
        required_fields = ['topic', 'num_questions']
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400
            if not data[field]:
                logger.error(f"Empty value for required field: {field}")
                return jsonify({'error': f'Empty value for required field: {field}'}), 400

        topic = data['topic']
        logger.info(f"Topic received: {topic}")

        try:
            num_questions = int(data['num_questions'])
            num_subtopics = int(data.get('num_subtopics', 3))  # Default to 3 if not provided
        except ValueError:
            logger.error("Invalid number format for num_questions or num_subtopics")
            return jsonify({'error': 'Invalid number format'}), 400

        # Validate ranges
        if not (1 <= num_questions <= 10):
            logger.error(f"num_questions out of range: {num_questions}")
            return jsonify({'error': 'Number of questions must be between 1 and 10'}), 400
        
        if not (1 <= num_subtopics <= 5):
            logger.error(f"num_subtopics out of range: {num_subtopics}")
            return jsonify({'error': 'Number of subtopics must be between 1 and 5'}), 400

        logger.info(f"Generating {num_questions} questions for topic: {topic} with {num_subtopics} subtopics")
        
        try:
            questions = generate_questions(topic=topic, num_questions=num_questions, num_subtopics=num_subtopics)
            
            # Update user statistics
            if current_user.is_authenticated:
                stats = Statistics.query.filter_by(user_id=current_user.id).first()
                if not stats:
                    stats = Statistics(user_id=current_user.id)
                    db.session.add(stats)
                stats.total_questions += num_questions
                stats.last_updated = datetime.utcnow()
                db.session.commit()
            
            return jsonify({'questions': questions})
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return jsonify({'error': 'Error generating questions'}), 500
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Error processing request'}), 500

@main.route('/settings', methods=['GET', 'POST'])
@login_required
def change_api_key():
    form = ChangeApiKeyForm()
    logging.warning(f"Form instantiated: {form is not None}")
    logging.warning(f"Request method: {request.method}")
    if request.method == 'POST':
        logging.warning(f"Form data: {request.form}")
        logging.warning(f"CSRF token in form: {request.form.get('csrf_token')}")
    env_path = Path('.env')
    openai_api_key = os.getenv('OPENAI_API_KEY', '')
    other_api_key = os.getenv('OTHER_API_KEY', '')

    if request.method == 'POST':
        openai_api_key = request.form.get('openai_api_key')
        other_api_key = request.form.get('other_api_key')

        # Salvar as chaves no arquivo .env
        if openai_api_key:
            set_key(env_path, 'OPENAI_API_KEY', openai_api_key)
        if other_api_key:
            set_key(env_path, 'OTHER_API_KEY', other_api_key)

        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('main.change_api_key'))

    return render_template(
        'settings.html',
        form=form,
        openai_api_key=openai_api_key,
        other_api_key=other_api_key
    )

@main.route('/docs')
@login_required
def docs():
    return render_template('docs.html')

@main.route('/answer')
@login_required
def answer_questions():
    return render_template('answer.html')

@main.route('/generate')
@login_required
def generate_questions_page():
    return render_template('generate.html')

@main.route('/statistics')
@login_required
def statistics():
    return render_template('statistics.html')

@main.route('/model-training')
@login_required
def model_training():
    return render_template('model_training.html')

@main.route('/model-selection')
@login_required
def model_selection():
    return render_template('model_selection.html')

@main.route('/api/random-question')
@login_required
def api_random_question():
    db = DatabaseManager()
    question = db.get_random_question()
    if not question:
        return {'error': 'Nenhuma questão encontrada'}, 404
    return {
        'id': question['id'],
        'question': question['question'],
        'options': question['options'],
        'topic': question.get('topic', ''),
        'subtopic': question.get('subtopic', ''),
        'difficulty': question.get('difficulty', 1)
    }

@main.route('/api/answer-question', methods=['POST'])
@login_required
def api_answer_question():
    data = request.get_json()
    question_id = data.get('question_id')
    selected_index = data.get('selected_index')
    db = DatabaseManager()
    question = db.get_question_by_id(question_id)
    if not question:
        return {'error': 'Questão não encontrada'}, 404
    correct_index = ord(question['correct_answer']) - ord('A')
    is_correct = (selected_index == correct_index)
    db.update_question_stats(question_id, is_correct)
    return {
        'correct': is_correct,
        'correct_index': correct_index,
        'explanation': question['explanation']
    }

@main.route('/api/report-question', methods=['POST'])
@login_required
def api_report_question():
    data = request.get_json()
    question_id = data.get('question_id')
    problem_type = data.get('problem_type')
    details = data.get('details', '')
    db = DatabaseManager()
    ok = db.report_question_problem(question_id, problem_type, details)
    if ok:
        return {'success': True}
    else:
        return {'success': False, 'error': 'Erro ao reportar problema'}, 400

@main.route('/api/statistics-web')
@login_required
def api_statistics_web():
    db = DatabaseManager()
    stats = db.get_statistics()
    return stats

@main.route('/api/process-documents', methods=['POST'])
@login_required
def process_documents():
    try:
        data = request.get_json()
        if not data or 'documents' not in data:
            return jsonify({'error': 'Dados inválidos'}), 400
            
        documents = data['documents']
        processed_documents = []
        
        for doc_path in documents:
            try:
                # Caminho completo do arquivo
                full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'resumos', doc_path)
                
                if not os.path.exists(full_path):
                    continue
                    
                # Extrair texto do PDF
                text = extract_text_from_pdf(full_path)
                
                # Dividir em chunks
                chunks = split_text_into_chunks(text)
                
                # Processar cada chunk com a IA
                processed_chunks = process_chunks_with_ai(chunks)
                
                # Obter o título do documento (nome do arquivo sem extensão)
                document_title = os.path.splitext(os.path.basename(doc_path))[0]
                
                # Deletar chunks antigos do mesmo documento
                TextChunk.query.filter_by(
                    document_title=document_title,
                    user_id=current_user.id
                ).delete()
                
                # Salvar novos chunks no banco de dados
                for chunk, processed in zip(chunks, processed_chunks):
                    text_chunk = TextChunk(
                        document_title=document_title,
                        chunk_text=chunk,
                        processed_text=processed['processed'],
                        user_id=current_user.id
                    )
                    db.session.add(text_chunk)
                
                db.session.commit()
                
                processed_documents.append({
                    'path': doc_path,
                    'status': 'Processado',
                    'processed_date': datetime.now().isoformat()
                })
                
            except Exception as e:
                current_app.logger.error(f'Erro ao processar documento {doc_path}: {str(e)}')
                db.session.rollback()
                continue
                
        return jsonify({
            'success': True,
            'processed_documents': processed_documents
        })
        
    except Exception as e:
        current_app.logger.error(f'Erro no processamento de documentos: {str(e)}')
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def split_text_into_chunks(text, chunk_size=1000):
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        if current_size + len(word) > chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1
            
    if current_chunk:
        chunks.append(' '.join(current_chunk))
        
    return chunks

def process_chunks_with_ai(chunks):
    client = get_openai_client()
    processed_chunks = []
    
    for chunk in chunks:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um assistente que processa textos técnicos."},
                    {"role": "user", "content": f"Processe o seguinte texto e extraia informações relevantes:\n\n{chunk}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            processed_chunks.append({
                'original': chunk,
                'processed': response.choices[0].message.content
            })
            
        except Exception as e:
            current_app.logger.error(f'Erro ao processar chunk com IA: {str(e)}')
            continue
            
    return processed_chunks

@main.route('/api/document-chunks/<document_title>')
@login_required
def get_document_chunks(document_title):
    try:
        chunks = TextChunk.query.filter_by(
            document_title=document_title,
            user_id=current_user.id
        ).all()
        
        return jsonify({
            'success': True,
            'chunks': [{
                'id': chunk.id,
                'chunk_text': chunk.chunk_text,
                'processed_text': chunk.processed_text,
                'created_at': chunk.created_at.isoformat()
            } for chunk in chunks]
        })
        
    except Exception as e:
        current_app.logger.error(f'Erro ao buscar chunks do documento {document_title}: {str(e)}')
        return jsonify({'error': str(e)}), 500 