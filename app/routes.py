from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from urllib.parse import urlparse
from app import db
from app.models import User, Question, Statistics, TextChunk, Domain, AIModel, Document, Topic, Summary
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
from openai import OpenAI
import traceback

# Importar usando caminho relativo
from app.api.openai_client import get_openai_client
from .database.db_manager import DatabaseManager
from app.utils.pdf_utils import extract_text_from_pdf, generate_topic_summary

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Adicionar o diretório src ao PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Carregar variáveis de ambiente
load_dotenv()

# Criar blueprint
main = Blueprint('main', __name__)

# Inicializar o gerenciador de banco de dados
db_manager = DatabaseManager()

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
    try:
        questions = db_manager.get_all_questions()
        return jsonify({
            'questions': [{
                'id': question['id'],
                'question': question['question'],
                'options': question['options'],
                'correct_answer': question['correct_answer'],
                'explanation': question['explanation'],
                'topic': question['topic'],
                'created_at': question['created_at']
            } for question in questions]
        })
    except Exception as e:
        logger.error(f"Error getting questions: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
        except ValueError:
            logger.error("Invalid number format for num_questions")
            return jsonify({'error': 'Invalid number format'}), 400

        # Validate ranges
        if not (1 <= num_questions <= 10):
            logger.error(f"num_questions out of range: {num_questions}")
            return jsonify({'error': 'Number of questions must be between 1 and 10'}), 400

        logger.info(f"Generating {num_questions} questions for topic: {topic}")
        
        try:
            client = get_openai_client()
            questions = generate_questions(
                topic=topic,
                num_questions=num_questions,
                api_key=os.getenv('OPENAI_API_KEY')
            )
            
            if not questions:
                logger.error("No questions generated")
                return jsonify({'error': 'Failed to generate questions'}), 500
            
            # Update user statistics
            if current_user.is_authenticated:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    # Check if stats exist for user
                    cursor.execute('''
                        SELECT id FROM user_statistics WHERE topic = ?
                    ''', (topic,))
                    stats = cursor.fetchone()
                    
                    if stats:
                        # Update existing stats
                        cursor.execute('''
                            UPDATE user_statistics 
                            SET questions_answered = questions_answered + ?,
                                last_session = CURRENT_TIMESTAMP
                            WHERE topic = ?
                        ''', (num_questions, topic))
                    else:
                        # Create new stats
                        cursor.execute('''
                            INSERT INTO user_statistics (
                                topic, questions_answered, correct_answers, last_session
                            ) VALUES (?, ?, 0, CURRENT_TIMESTAMP)
                        ''', (topic, num_questions))
                    
                    conn.commit()
            
            return jsonify({'questions': questions})
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
    """Renderiza a página de seleção de modelos"""
    try:
        # Buscar todos os modelos
        models = AIModel.query.order_by(AIModel.model_type, AIModel.created_at.desc()).all()
        
        # Contar modelos por tipo
        model_counts = {
            'question': len([m for m in models if m.model_type == 'question']),
            'answer': len([m for m in models if m.model_type == 'answer']),
            'distractor': len([m for m in models if m.model_type == 'distractor'])
        }
        
        # Buscar modelos padrão
        default_models = {
            'question': next((m for m in models if m.model_type == 'question' and m.is_default), None),
            'answer': next((m for m in models if m.model_type == 'answer' and m.is_default), None),
            'distractor': next((m for m in models if m.model_type == 'distractor' and m.is_default), None)
        }
        
        return render_template('model_selection.html', 
                             models=models,
                             model_counts=model_counts,
                             default_models=default_models)
    except Exception as e:
        logger.error(f"Erro ao carregar página de seleção de modelos: {str(e)}")
        flash('Erro ao carregar modelos', 'error')
        return redirect(url_for('main.index'))

@main.route('/api/add-model', methods=['POST'])
@login_required
def add_model():
    """Adiciona um novo modelo de IA"""
    try:
        logger.info("Iniciando adição de novo modelo")
        data = request.form
        
        # Validar dados
        if not all(key in data for key in ['model_name', 'model_type', 'model_id']):
            logger.error("Dados incompletos no formulário")
            flash('Por favor, preencha todos os campos', 'error')
            return redirect(url_for('main.model_selection'))
        
        # Validar tipo do modelo
        if data['model_type'] not in ['question', 'answer', 'distractor']:
            logger.error(f"Tipo de modelo inválido: {data['model_type']}")
            flash('Tipo de modelo inválido', 'error')
            return redirect(url_for('main.model_selection'))
        
        # Criar modelo
        model = AIModel(
            name=data['model_name'],
            model_type=data['model_type'],
            model_id=data['model_id']
        )
        
        logger.info(f"Adicionando modelo: {model.name} ({model.model_type})")
        db.session.add(model)
        db.session.commit()
        
        flash('Modelo adicionado com sucesso!', 'success')
        logger.info("Modelo adicionado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao adicionar modelo: {str(e)}")
        db.session.rollback()
        flash('Erro ao adicionar modelo', 'error')
    
    return redirect(url_for('main.model_selection'))

@main.route('/api/save-model-selection', methods=['POST'])
@login_required
def save_model_selection():
    """Salva a seleção de modelos padrão"""
    try:
        # Resetar todos os modelos para não padrão
        AIModel.query.update({AIModel.is_default: False})
        
        # Definir os novos modelos padrão
        question_model_id = request.form.get('question_model')
        answer_model_id = request.form.get('answer_model')
        distractor_model_id = request.form.get('distractor_model')
        
        if question_model_id:
            model = AIModel.query.get(question_model_id)
            if model:
                model.is_default = True
        
        if answer_model_id:
            model = AIModel.query.get(answer_model_id)
            if model:
                model.is_default = True
        
        if distractor_model_id:
            model = AIModel.query.get(distractor_model_id)
            if model:
                model.is_default = True
        
        db.session.commit()
        flash('Configurações salvas com sucesso!', 'success')
    except Exception as e:
        logger.error(f"Erro ao salvar seleção de modelos: {str(e)}")
        flash('Erro ao salvar configurações', 'error')
    return redirect(url_for('main.model_selection'))

@main.route('/api/get-default-models', methods=['GET'])
@login_required
def get_default_models():
    """Retorna os modelos padrão configurados"""
    try:
        default_models = AIModel.query.filter_by(is_default=True).all()
        return jsonify({
            'question_model': next((m.model_id for m in default_models if m.model_type == 'question'), None),
            'answer_model': next((m.model_id for m in default_models if m.model_type == 'answer'), None),
            'distractor_model': next((m.model_id for m in default_models if m.model_type == 'distractor'), None)
        })
    except Exception as e:
        logger.error(f"Erro ao obter modelos padrão: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/random-question')
@login_required
def api_random_question():
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM questions 
                ORDER BY RANDOM() 
                LIMIT 1
            ''')
            question = cursor.fetchone()
            
            if question:
                return jsonify({
                    'id': question['id'],
                    'question': question['question'],
                    'options': json.loads(question['options']),
                    'correct_answer': question['correct_answer'],
                    'explanation': question['explanation'],
                    'topic': question['topic']
                })
            else:
                return jsonify({'error': 'No questions available'}), 404
    except Exception as e:
        logger.error(f"Error getting random question: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/answer-question', methods=['POST'])
@login_required
def api_answer_question():
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        answer = data.get('answer')
        
        if not question_id or not answer:
            return jsonify({'error': 'Missing question_id or answer'}), 400
            
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT correct_answer FROM questions 
                WHERE id = ?
            ''', (question_id,))
            question = cursor.fetchone()
            
            if not question:
                return jsonify({'error': 'Question not found'}), 404
                
            is_correct = answer == question['correct_answer']
            
            # Update statistics
            cursor.execute('''
                UPDATE user_statistics 
                SET correct_answers = correct_answers + ?
                WHERE topic = (
                    SELECT topic FROM questions WHERE id = ?
                )
            ''', (1 if is_correct else 0, question_id))
            
            conn.commit()
            
            return jsonify({
                'is_correct': is_correct,
                'correct_answer': question['correct_answer']
            })
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/report-question', methods=['POST'])
@login_required
def api_report_question():
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        reason = data.get('reason')
        
        if not question_id or not reason:
            return jsonify({'error': 'Missing question_id or reason'}), 400
            
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reported_questions (
                    question_id, reason, reported_by, reported_at
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (question_id, reason, current_user.id))
            conn.commit()
            
            return jsonify({'message': 'Question reported successfully'})
    except Exception as e:
        logger.error(f"Error reporting question: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/statistics-web')
@login_required
def api_statistics_web():
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT topic, 
                       SUM(questions_answered) as total_questions,
                       SUM(correct_answers) as total_correct
                FROM user_statistics
                GROUP BY topic
            ''')
            stats = cursor.fetchall()
            
            return jsonify({
                'statistics': [{
                    'topic': row['topic'],
                    'total_questions': row['total_questions'],
                    'total_correct': row['total_correct'],
                    'accuracy': (row['total_correct'] / row['total_questions'] * 100) if row['total_questions'] > 0 else 0
                } for row in stats]
            })
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/process-documents', methods=['POST'])
@login_required
def process_documents():
    try:
        data = request.get_json()
        logger.info(f'[PROCESS-DOCS] Dados recebidos: {data}')
        if not data or 'documents' not in data:
            logger.error('[PROCESS-DOCS] Dados inválidos recebidos no processamento')
            return jsonify({'error': 'Dados inválidos'}), 400
        
        documents = data['documents']
        results = []
        import re
        
        for doc_path in documents:
            try:
                uploads_dir = os.path.join('data', 'uploads', 'resumos')
                full_path = os.path.join(uploads_dir, doc_path)
                logger.info(f'[PROCESS-DOCS] Processando documento: {doc_path} (caminho: {full_path})')
                
                if not os.path.exists(full_path):
                    logger.warning(f'[PROCESS-DOCS] Arquivo não encontrado: {full_path}')
                    results.append({'name': doc_path, 'status': 'Erro', 'message': 'Arquivo não encontrado'})
                    continue
                
                # Extrair texto do PDF
                text = extract_text_from_pdf(full_path)
                logger.info(f'[PROCESS-DOCS] Texto extraído do PDF ({doc_path}): {len(text)} caracteres')
                
                if not text.strip():
                    logger.error(f'[PROCESS-DOCS] Texto extraído está vazio para o documento {doc_path}')
                    results.append({'name': doc_path, 'status': 'Erro', 'message': 'Não foi possível extrair texto do documento'})
                    continue
                
                # Separar texto original em blocos por tópico
                original_blocks = []
                current_block = ''
                current_topic = None
                
                logger.info(f'[PROCESS-DOCS] Iniciando extração de tópicos do documento {doc_path}')
                
                # Padrão para identificar tópicos (números seguidos de ponto ou parênteses)
                topic_pattern = re.compile(r'^\s*(\d+[\.\)])\s*(.*?)$', re.MULTILINE)
                
                # Encontrar todos os tópicos no texto
                matches = list(topic_pattern.finditer(text))
                logger.info(f'[PROCESS-DOCS] Encontrados {len(matches)} tópicos no documento {doc_path}')
                
                for i, match in enumerate(matches):
                    topic_number = match.group(1).strip()
                    topic_title = match.group(2).strip()
                    
                    # Determinar o conteúdo do tópico
                    start_pos = match.end()
                    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    content = text[start_pos:end_pos].strip()
                    
                    logger.info(f'[PROCESS-DOCS] Tópico {topic_number} encontrado: {topic_title}')
                    logger.info(f'[PROCESS-DOCS] Tamanho do conteúdo: {len(content)} caracteres')
                    
                    original_blocks.append({
                        'number': topic_number,
                        'title': topic_title,
                        'content': content
                    })
                
                # Salvar os tópicos no banco de dados
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Primeiro, verificar se já existem tópicos para este documento
                    cursor.execute('SELECT COUNT(*) FROM topic_summaries WHERE document_title = ?', (doc_path,))
                    existing_count = cursor.fetchone()[0]
                    logger.info(f'[PROCESS-DOCS] Documento {doc_path} já possui {existing_count} tópicos no banco')
                
                    # Log da estrutura da tabela
                    cursor.execute("PRAGMA table_info(topic_summaries)")
                    columns = cursor.fetchall()
                    logger.info(f'[PROCESS-DOCS] Estrutura da tabela topic_summaries: {columns}')
                    
                    for block in original_blocks:
                        try:
                            # Verificar se o tópico já existe
                            cursor.execute('''
                                SELECT id FROM topic_summaries 
                                WHERE document_title = ? AND topic = ?
                            ''', (doc_path, block['number']))
                            
                            existing = cursor.fetchone()
                            if existing:
                                logger.info(f'[PROCESS-DOCS] Tópico {block["number"]} já existe para o documento {doc_path}')
                                continue
                            
                            # Log dos dados antes de inserir
                            logger.info(f'[PROCESS-DOCS] Inserindo tópico {block["number"]} para o documento {doc_path}')
                            logger.info(f'[PROCESS-DOCS] Dados do tópico: {block}')
                            
                            # Extrair domínios do título do tópico
                            domains = []
                            if "Gerenciamento da Integração" in block['title'] or "Metodologias de Gerenciamento" in doc_path:
                                domains.append("Gerenciamento da Integração")
                            if "Gerenciamento do Escopo" in block['title']:
                                domains.append("Gerenciamento do Escopo")
                            if "Gerenciamento do Tempo" in block['title']:
                                domains.append("Gerenciamento do Tempo")
                            if "Gerenciamento do Custo" in block['title']:
                                domains.append("Gerenciamento do Custo")
                            if "Gerenciamento da Qualidade" in block['title']:
                                domains.append("Gerenciamento da Qualidade")
                            if "Gerenciamento dos Recursos" in block['title']:
                                domains.append("Gerenciamento dos Recursos")
                            if "Gerenciamento das Comunicações" in block['title']:
                                domains.append("Gerenciamento das Comunicações")
                            if "Gerenciamento dos Riscos" in block['title']:
                                domains.append("Gerenciamento dos Riscos")
                            if "Gerenciamento das Aquisições" in block['title']:
                                domains.append("Gerenciamento das Aquisições")
                            if "Gerenciamento das Partes Interessadas" in block['title']:
                                domains.append("Gerenciamento das Partes Interessadas")

                            # Se não encontrou domínios específicos, usar o domínio do documento
                            if not domains:
                                if "Metodologias de Gerenciamento" in doc_path:
                                    domains.append("Gerenciamento da Integração")
                                elif "Gerenciamento do Escopo" in doc_path:
                                    domains.append("Gerenciamento do Escopo")
                                elif "Gerenciamento do Tempo" in doc_path:
                                    domains.append("Gerenciamento do Tempo")
                                elif "Gerenciamento do Custo" in doc_path:
                                    domains.append("Gerenciamento do Custo")
                                elif "Gerenciamento da Qualidade" in doc_path:
                                    domains.append("Gerenciamento da Qualidade")
                                elif "Gerenciamento dos Recursos" in doc_path:
                                    domains.append("Gerenciamento dos Recursos")
                                elif "Gerenciamento das Comunicações" in doc_path:
                                    domains.append("Gerenciamento das Comunicações")
                                elif "Gerenciamento dos Riscos" in doc_path:
                                    domains.append("Gerenciamento dos Riscos")
                                elif "Gerenciamento das Aquisições" in doc_path:
                                    domains.append("Gerenciamento das Aquisições")
                                elif "Gerenciamento das Partes Interessadas" in doc_path:
                                    domains.append("Gerenciamento das Partes Interessadas")

                            cursor.execute('''
                                INSERT INTO topic_summaries (
                                    document_title, topic, summary, domains, created_at
                                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                            ''', (
                                doc_path,
                                block['number'],
                                block['content'],
                                json.dumps(domains)
                            ))
                            
                            # Verificar se o tópico foi inserido
                            cursor.execute('''
                                SELECT id FROM topic_summaries 
                                WHERE document_title = ? AND topic = ?
                            ''', (doc_path, block['number']))
                            
                            inserted = cursor.fetchone()
                            if inserted:
                                logger.info(f'[PROCESS-DOCS] Tópico {block["number"]} inserido com sucesso. ID: {inserted[0]}')
                            else:
                                logger.error(f'[PROCESS-DOCS] Falha ao inserir tópico {block["number"]}')
                            
                        except Exception as e:
                            logger.error(f'[PROCESS-DOCS] Erro ao salvar tópico {block["number"]} no banco: {str(e)}')
                            logger.error(f'[PROCESS-DOCS] Stack trace: {traceback.format_exc()}')
                            continue
                    
                    conn.commit()
                    
                    # Verificar total de tópicos após o processamento
                    cursor.execute('SELECT COUNT(*) FROM topic_summaries WHERE document_title = ?', (doc_path,))
                    final_count = cursor.fetchone()[0]
                    logger.info(f'[PROCESS-DOCS] Total de tópicos após processamento: {final_count}')
                    
                    logger.info(f'[PROCESS-DOCS] Todos os tópicos do documento {doc_path} foram salvos no banco')
                
                # Retornar apenas os tópicos extraídos, sem processamento
                results.append({
                    'name': doc_path, 
                    'status': 'Extraído', 
                    'message': f'Extração concluída com sucesso. {len(original_blocks)} tópicos encontrados.',
                    'topics': original_blocks
                })
                
            except Exception as e:
                current_app.logger.error(f'[PROCESS-DOCS] Erro ao processar documento {doc_path}: {str(e)}')
                current_app.logger.error(f'[PROCESS-DOCS] Stack trace: {traceback.format_exc()}')
                results.append({'name': doc_path, 'status': 'Erro', 'message': str(e)})
                continue
                
        logger.info(f'[PROCESS-DOCS] Resultado final da extração: {results}')
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        current_app.logger.error(f'[PROCESS-DOCS] Erro no processamento de documentos: {str(e)}')
        current_app.logger.error(f'[PROCESS-DOCS] Stack trace: {traceback.format_exc()}')
        return jsonify({'error': str(e)}), 500

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
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM text_chunks 
                WHERE document_title = ?
                ORDER BY chunk_index
            ''', (document_title,))
            chunks = cursor.fetchall()
            
            return jsonify({
                'chunks': [{
                    'id': chunk['id'],
                    'content': chunk['content'],
                    'chunk_index': chunk['chunk_index'],
                    'document_title': chunk['document_title'],
                    'created_at': chunk['created_at']
                } for chunk in chunks]
            })
    except Exception as e:
        logger.error(f"Error getting document chunks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/list-documents', methods=['GET'])
def list_documents():
    try:
        uploads_dir = os.path.join('data', 'uploads', 'resumos')
        logger.info(f'[LIST] Verificando diretório: {uploads_dir}')
        
        if not os.path.exists(uploads_dir):
            logger.warning(f'[LIST] Diretório não encontrado: {uploads_dir}')
            return jsonify({'documents': []})
        
        # Listar arquivos PDF
        pdf_files = [f for f in os.listdir(uploads_dir) if f.lower().endswith('.pdf')]
        logger.info(f'[LIST] Arquivos PDF encontrados: {pdf_files}')
        
        documents = []
        
        for pdf_file in pdf_files:
            # Verifica se existem resumos para este documento
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar a estrutura atual da tabela
                cursor.execute("PRAGMA table_info(topic_summaries)")
                columns = cursor.fetchall()
                logger.info(f"[LIST] Estrutura atual da tabela topic_summaries: {columns}")
                
                logger.info(f"[LIST] Verificando resumos para documento: {pdf_file}")
                
                # Log da query SQL
                query = "SELECT COUNT(*) FROM topic_summaries WHERE document_title = ?"
                logger.info(f"[LIST] Executando query: {query} com parâmetro: {pdf_file}")
                
                # Usa o nome do arquivo com extensão para buscar no banco
                cursor.execute(query, (pdf_file,))
                count = cursor.fetchone()[0]
                logger.info(f"[LIST] Documento {pdf_file}: {count} resumos encontrados")
                
                # Busca detalhes dos resumos
                query = "SELECT id, topic, summary, created_at FROM topic_summaries WHERE document_title = ?"
                logger.info(f"[LIST] Executando query: {query} com parâmetro: {pdf_file}")
                
                cursor.execute(query, (pdf_file,))
                summaries = cursor.fetchall()
                logger.info(f"[LIST] Detalhes dos resumos: {summaries}")
                
                # Log dos títulos existentes na tabela
                cursor.execute("SELECT DISTINCT document_title FROM topic_summaries")
                existing_titles = [row[0] for row in cursor.fetchall()]
                logger.info(f"[LIST] Títulos existentes na tabela: {existing_titles}")
                
                # Determina se o documento está processado
                is_processed = count > 0
                logger.info(f"[LIST] Documento {pdf_file} está processado: {is_processed} (count: {count})")
                
                documents.append({
                    'name': pdf_file,
                    'processed': is_processed
                })
        
        logger.info(f'[LIST] Lista final de documentos: {documents}')
        return jsonify({'documents': documents})
        
    except Exception as e:
        logger.error(f'[LIST] Erro ao listar documentos: {str(e)}')
        logger.error(f'[LIST] Stack trace: {traceback.format_exc()}')
        current_app.logger.error(f'[UPLOAD] Erro ao salvar arquivo: {str(e)}')
        return jsonify({'error': f'Erro ao salvar arquivo: {str(e)}'}), 500

@main.route('/api/delete-document', methods=['DELETE'])
def delete_document():
    data = request.get_json()
    filename = data.get('filename')
    logger.info(f'[DELETE] Requisição para remover arquivo: {filename}')
    if not filename:
        logger.error('[DELETE] Nome do arquivo não informado.')
        return jsonify({'error': 'Nome do arquivo não informado.'}), 400
    uploads_dir = os.path.join('data', 'uploads', 'resumos')
    file_path = os.path.join(uploads_dir, filename)
    if not os.path.exists(file_path):
        logger.warning(f'[DELETE] Arquivo não encontrado: {file_path}')
        return jsonify({'error': 'Arquivo não encontrado.'}), 404
    try:
        os.remove(file_path)
        logger.info(f'[DELETE] Arquivo removido: {file_path}')
        # Remover chunks do banco de dados
        # Usa o nome do arquivo com extensão para buscar no banco
        if current_user.is_authenticated:
            deleted = TextChunk.query.filter_by(document_title=filename, user_id=current_user.id).delete()
            from app import db
            db.session.commit()
            current_app.logger.info(f'[DELETE] Removidos {deleted} chunks do documento {filename} para o usuário {current_user.id}')
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f'[DELETE] Erro ao remover documento ou chunks: {str(e)}')
        return jsonify({'error': str(e)}), 500

@main.route('/db-viewer')
@login_required
def db_viewer():
    from app.models import TextChunk, Question, User
    chunks = TextChunk.query.limit(50).all()
    questions = Question.query.limit(20).all()
    users = User.query.limit(10).all()
    return render_template('db_viewer.html', chunks=chunks, questions=questions, users=users)

@main.route('/api/extract-topics', methods=['POST'])
@login_required
def extract_topics():
    try:
        data = request.get_json()
        if not data or 'document' not in data:
            return jsonify({'error': 'Documento não informado'}), 400
        doc_path = data['document']
        uploads_dir = os.path.join('data', 'uploads', 'resumos')
        full_path = os.path.join(uploads_dir, doc_path)
        if not os.path.exists(full_path):
            return jsonify({'error': 'Arquivo não encontrado'}), 404
        text = extract_text_from_pdf(full_path)
        import re
        original_blocks = []
        current_block = ''
        current_topic = None
        for line in text.splitlines():
            match = re.match(r'^(\d+)(?:\.\d+)*-\s*(.*)', line.strip())
            if match:
                main_topic = match.group(1)
                if current_topic is not None and main_topic != current_topic:
                    original_blocks.append({'topic': current_topic, 'text': current_block.strip()})
                    current_block = ''
                current_topic = main_topic
                current_block += ('' if current_block == '' else '\n') + match.group(2)
            else:
                current_block += '\n' + line
        if current_block and current_topic is not None:
            original_blocks.append({'topic': current_topic, 'text': current_block.strip()})
        # Filtrar apenas tópicos com texto não vazio
        original_blocks = [b for b in original_blocks if b['text'].strip()]
        # Remover quebras de linha para exibição em parágrafo
        for b in original_blocks:
            b['text'] = b['text'].replace('\n', ' ')
        return jsonify({'success': True, 'topics': original_blocks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/process_topic', methods=['POST'])
def process_topic():
    try:
        data = request.get_json()
        topic = data.get('topic')
        document_title = data.get('document_title')
        
        logger.info(f"[PROCESS-TOPIC] Recebida requisição para processar tópico do documento: {document_title}")
        logger.info(f"[PROCESS-TOPIC] Tópico: {topic}")
        
        if not topic or not document_title:
            logger.error("[PROCESS-TOPIC] Tópico ou título do documento não fornecidos")
            return jsonify({'error': 'Tópico e título do documento são obrigatórios'}), 400
            
        # Extrair texto do PDF
        # Não adiciona .pdf se já existir no nome do arquivo
        if not document_title.lower().endswith('.pdf'):
            document_title = f"{document_title}.pdf"
            
        pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'resumos', document_title)
        logger.info(f"[PROCESS-TOPIC] Caminho do arquivo: {pdf_path}")
        
        try:
            text = extract_text_from_pdf(pdf_path)
            logger.info(f"[PROCESS-TOPIC] Texto extraído com sucesso: {len(text)} caracteres")
        except Exception as e:
            logger.error(f"[PROCESS-TOPIC] Erro ao extrair texto do PDF: {str(e)}")
            return jsonify({'error': f'Erro ao extrair texto do PDF: {str(e)}'}), 500
            
        # Gerar resumo
        try:
            summary_data = generate_topic_summary(topic, text)
            if not summary_data:
                logger.error("[PROCESS-TOPIC] Falha ao gerar resumo do tópico")
                return jsonify({'error': 'Falha ao gerar resumo do tópico'}), 500
                
            logger.info("[PROCESS-TOPIC] Resumo gerado com sucesso")
            
            # Salvar no banco de dados
            try:
                conn = db_manager.get_connection()
                cursor = conn.cursor()
                
                # Verificar se já existe um resumo para este tópico
                cursor.execute("""
                    SELECT id FROM topic_summaries 
                    WHERE document_title = ? AND topic = ?
                """, (document_title, topic))
                
                existing_summary = cursor.fetchone()
                
                if existing_summary:
                    # Atualizar resumo existente
                    cursor.execute("""
                        UPDATE topic_summaries 
                        SET summary = ?, key_points = ?, practical_examples = ?,
                            pmbok_references = ?, domains = ?
                        WHERE id = ?
                    """, (
                        summary_data['summary'],
                        json.dumps(summary_data['key_points']),
                        json.dumps(summary_data['practical_examples']),
                        json.dumps(summary_data['pmbok_references']),
                        json.dumps(summary_data['domains']),
                        existing_summary[0]
                    ))
                    summary_id = existing_summary[0]
                    logger.info(f"[PROCESS-TOPIC] Resumo atualizado com ID: {summary_id}")
                else:
                    # Inserir novo resumo
                    cursor.execute("""
                        INSERT INTO topic_summaries 
                        (document_title, topic, summary, key_points, practical_examples,
                         pmbok_references, domains)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        document_title,
                        topic,
                        summary_data['summary'],
                        json.dumps(summary_data['key_points']),
                        json.dumps(summary_data['practical_examples']),
                        json.dumps(summary_data['pmbok_references']),
                        json.dumps(summary_data['domains'])
                    ))
                    summary_id = cursor.lastrowid
                    logger.info(f"[PROCESS-TOPIC] Novo resumo salvo com ID: {summary_id}")
                    
                conn.commit()
                return jsonify({
                    'success': True,
                    'summary_id': summary_id,
                    'summary': summary_data
                })
                
            except Exception as e:
                logger.error(f"[PROCESS-TOPIC] Erro ao salvar no banco de dados: {str(e)}")
                logger.error(f"[PROCESS-TOPIC] Tipo do erro: {type(e)}")
                logger.error(f"[PROCESS-TOPIC] Stack trace: {traceback.format_exc()}")
                return jsonify({'error': f'Erro ao salvar no banco de dados: {str(e)}'}), 500
                
        except Exception as e:
            logger.error(f"[PROCESS-TOPIC] Erro ao gerar resumo: {str(e)}")
            logger.error(f"[PROCESS-TOPIC] Tipo do erro: {type(e)}")
            logger.error(f"[PROCESS-TOPIC] Stack trace: {traceback.format_exc()}")
            return jsonify({'error': f'Erro ao gerar resumo: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"[PROCESS-TOPIC] Erro geral: {str(e)}")
        logger.error(f"[PROCESS-TOPIC] Tipo do erro: {type(e)}")
        logger.error(f"[PROCESS-TOPIC] Stack trace: {traceback.format_exc()}")
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

def process_questions_with_ai(questions):
    """Process questions using AI to enhance their content."""
    try:
        processed_questions = []
        for question in questions:
            # Extract question data
            question_id = question['id']
            current_question = question['question']
            current_options = json.loads(question['options'])
            current_answer = question['correct_answer']
            current_explanation = question['explanation']
            topic = question['topic']
            
            # Prepare the prompt for AI
            prompt = f"""
            Please enhance the following project management question:
            
            Topic: {topic}
            Question: {current_question}
            Options: {current_options}
            Correct Answer: {current_answer}
            Explanation: {current_explanation}
            
            Please provide:
            1. An enhanced question
            2. Updated options
            3. The correct answer
            4. A more detailed explanation
            """
            
            # Get AI response
            response = get_ai_response(prompt)
            
            # Parse AI response
            enhanced_content = parse_ai_response(response)
            
            processed_questions.append({
                'id': question_id,
                'question': enhanced_content.get('question', current_question),
                'options': enhanced_content.get('options', current_options),
                'correct_answer': enhanced_content.get('correct_answer', current_answer),
                'explanation': enhanced_content.get('explanation', current_explanation)
            })
        
        return processed_questions
        
    except Exception as e:
        logger.error(f"Error processing questions with AI: {str(e)}")
        raise

@main.route('/api/save-chunks', methods=['POST'])
@login_required
def save_chunks():
    try:
        data = request.get_json()
        chunks = data.get('chunks', [])
        
        if not chunks:
            return jsonify({'error': 'No chunks provided'}), 400
            
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            for chunk in chunks:
                cursor.execute('''
                    INSERT INTO text_chunks (
                        content, chunk_index, document_title, created_at
                    ) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    chunk['content'],
                    chunk['chunk_index'],
                    chunk['document_title']
                ))
            
            conn.commit()
            
            return jsonify({
                'message': 'Chunks saved successfully',
                'chunks_saved': len(chunks)
            })
    except Exception as e:
        logger.error(f"Error saving chunks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/delete-chunks', methods=['POST'])
@login_required
def delete_chunks():
    try:
        data = request.get_json()
        chunk_ids = data.get('chunk_ids', [])
        
        if not chunk_ids:
            return jsonify({'error': 'No chunk IDs provided'}), 400
            
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete chunks
            cursor.execute('''
                DELETE FROM text_chunks 
                WHERE id IN ({})
            '''.format(','.join('?' * len(chunk_ids))), chunk_ids)
            
            conn.commit()
            
            return jsonify({
                'message': 'Chunks deleted successfully',
                'chunks_deleted': cursor.rowcount
            })
    except Exception as e:
        logger.error(f"Error deleting chunks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/prompt/<int:prompt_id>')
def get_prompt(prompt_id):
    prompt = db.get_prompt(prompt_id)
    if prompt:
        return jsonify(prompt)
    return jsonify({'error': 'Prompt não encontrado'}), 404

@main.route('/api/chunk/<int:chunk_id>')
def get_chunk(chunk_id):
    chunk = db.get_chunk(chunk_id)
    if chunk:
        return jsonify(chunk)
    return jsonify({'error': 'Chunk não encontrado'}), 404

@main.route('/api/question/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
            conn.commit()
            
            return jsonify({'message': 'Question deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting question: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/domains', methods=['GET'])
def get_domains():
    """Retorna a lista de domínios do PMBOK"""
    try:
        domains = Domain.query.all()
        return jsonify({
            'success': True,
            'domains': [{'id': domain.id, 'name': domain.name} for domain in domains]
        })
    except Exception as e:
        logger.error(f"Erro ao buscar domínios: {str(e)}")
        return jsonify({'error': 'Erro ao buscar domínios'}), 500

@main.route('/api/generate-questions', methods=['POST'])
@login_required
def generate_questions_endpoint():
    try:
        data = request.get_json()
        domain = data.get('domain')
        num_questions = data.get('num_questions', 5)
        
        logger.info(f"[GENERATE-QUESTIONS] Received request with domain: {domain}, num_questions: {num_questions}")
        
        if not domain:
            logger.error("[GENERATE-QUESTIONS] Missing required field: domain")
            return jsonify({'error': 'Domain is required'}), 400
            
        # Buscar o domínio no banco de dados
        domain_obj = Domain.query.filter_by(name=domain).first()
        if not domain_obj:
            logger.error(f"[GENERATE-QUESTIONS] Domain not found: {domain}")
            return jsonify({'error': 'Domain not found'}), 404
            
        # Buscar modelos padrão
        default_models = AIModel.query.filter_by(is_default=True).all()
        if not default_models:
            logger.error("[GENERATE-QUESTIONS] No default models found")
            return jsonify({'error': 'No default models configured'}), 400
            
        # Mapear modelos por tipo
        model_map = {model.model_type: model.model_id for model in default_models}
        
        # Buscar resumos relacionados ao domínio
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            def normalize_unicode(text):
                """Normaliza texto para lidar com caracteres Unicode escapados"""
                import unicodedata
                # Primeiro tenta decodificar se for bytes
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                # Remove escapes Unicode
                text = text.encode('utf-8').decode('unicode-escape')
                # Normaliza para forma composta
                text = unicodedata.normalize('NFC', text)
                return text.lower().strip()

            # Primeiro, vamos verificar o conteúdo da tabela
            cursor.execute("SELECT id, document_title, domains, summary FROM topic_summaries")
            all_summaries = cursor.fetchall()
            logger.info(f"[GENERATE-QUESTIONS] Total de registros na tabela: {len(all_summaries)}")
            logger.info("[GENERATE-QUESTIONS] Conteúdo da tabela topic_summaries:")
            
            # Lista para armazenar os IDs dos resumos encontrados
            found_summary_ids = []
            
            for summary in all_summaries:
                try:
                    domains_json = json.loads(summary[2])
                    logger.info(f"[GENERATE-QUESTIONS] Documento: {summary[1]}")
                    logger.info(f"[GENERATE-QUESTIONS] Domínios (raw): {summary[2]}")
                    logger.info(f"[GENERATE-QUESTIONS] Domínios (parsed): {domains_json}")
                    logger.info(f"[GENERATE-QUESTIONS] Tamanho do resumo: {len(summary[3]) if summary[3] else 0} caracteres")
                    
                    # Verifica se o domínio está presente e se tem resumo
                    if isinstance(domains_json, list) and summary[3]:
                        for domain_item in domains_json:
                            if isinstance(domain_item, dict):
                                domain_name = domain_item.get('name', '')
                            else:
                                domain_name = domain_item
                                
                            if normalize_unicode(domain_name) == normalize_unicode(domain):
                                found_summary_ids.append(summary[0])
                                logger.info(f"[GENERATE-QUESTIONS] Domínio encontrado em resumo ID: {summary[0]}")
                                break
                except Exception as e:
                    logger.error(f"[GENERATE-QUESTIONS] Erro ao processar domínios: {e}")

            if found_summary_ids:
                # Escolhe um resumo aleatoriamente
                import random
                selected_id = random.choice(found_summary_ids)
                logger.info(f"[GENERATE-QUESTIONS] Resumo selecionado aleatoriamente: ID {selected_id}")
                
                # Busca o resumo completo
                cursor.execute("""
                    SELECT 
                        summary,
                        key_points,
                        practical_examples,
                        pmbok_references,
                        domains,
                        document_title
                    FROM topic_summaries 
                    WHERE id = ?
                """, (selected_id,))
                
                result = cursor.fetchone()
                if result and result[0]:
                    summary_data = {
                        'summary': result[0],
                        'key_points': json.loads(result[1]) if result[1] else [],
                        'practical_examples': json.loads(result[2]) if result[2] else [],
                        'pmbok_references': json.loads(result[3]) if result[3] else [],
                        'domains': result[4]
                    }
                    logger.info(f"[GENERATE-QUESTIONS] Processando resumo para domínio {domain}")
                    logger.info(f"[GENERATE-QUESTIONS] Primeiros 100 caracteres do resumo: {result[0][:100]}")
                    
                    # Busca todos os resumos usados para exibição
                    used_summaries = []
                    for summary_id in found_summary_ids:
                        cursor.execute("""
                            SELECT document_title, summary 
                            FROM topic_summaries 
                            WHERE id = ?
                        """, (summary_id,))
                        summary_result = cursor.fetchone()
                        if summary_result:
                            used_summaries.append({
                                'document': summary_result[0],
                                'summary': summary_result[1]
                            })
                    
                    from app.api.openai_client import generate_questions
                    questions = generate_questions(
                        topic=domain,
                        num_questions=num_questions,
                        api_key=os.getenv('OPENAI_API_KEY'),
                        summary=result[0]  # Passa o resumo encontrado
                    )
                    if not questions:
                        logger.error("[GENERATE-QUESTIONS] No questions generated")
                        return jsonify({'error': 'Failed to generate questions'}), 500
                    
                    # Adiciona os resumos usados à resposta
                    return jsonify({
                        'questions': questions,
                        'used_summaries': used_summaries
                    })
                else:
                    logger.error(f"[GENERATE-QUESTIONS] Resumo não encontrado para o ID: {selected_id}")
                    return jsonify({'error': 'No summary found for domain'}), 404
            else:
                logger.error(f"[GENERATE-QUESTIONS] No summary found for domain: {domain}")
                return jsonify({'error': 'No summary found for domain'}), 404
            
    except Exception as e:
        logger.error(f"[GENERATE-QUESTIONS] Error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@main.route('/api/database-status')
@login_required
def api_database_status():
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute('SELECT COUNT(*) FROM questions')
            question_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM text_chunks')
            chunk_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM user_statistics')
            stats_count = cursor.fetchone()[0]
            
            return jsonify({
                'question_count': question_count,
                'chunk_count': chunk_count,
                'stats_count': stats_count,
                'database_path': db_manager.questions_db
            })
    except Exception as e:
        logger.error(f"Error getting database status: {str(e)}")
        return jsonify({'error': str(e)}), 500

def parse_ai_response(response_text):
    """Parse the AI response into structured data."""
    try:
        # Try to parse as JSON first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # If not JSON, try to parse sections
        sections = {
            'summary': '',
            'key_points': [],
            'practical_examples': [],
            'pmbok_references': []
        }
        
        current_section = None
        for line in response_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            if line.lower().startswith('summary:'):
                current_section = 'summary'
                continue
            elif line.lower().startswith('key points:'):
                current_section = 'key_points'
                continue
            elif line.lower().startswith('practical examples:'):
                current_section = 'practical_examples'
                continue
            elif line.lower().startswith('pmbok references:'):
                current_section = 'pmbok_references'
                continue
                
            # Add content to current section
            if current_section:
                if current_section == 'summary':
                    sections['summary'] += line + ' '
                else:
                    if line.startswith('- '):
                        line = line[2:]
                    sections[current_section].append(line)
        
        # Clean up summary
        sections['summary'] = sections['summary'].strip()
        
        return sections
        
    except Exception as e:
        logger.error(f"Error parsing AI response: {str(e)}")
        return None 

def get_ai_response(prompt):
    """Get response from OpenAI API."""
    try:
        client = get_openai_client()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos com profundo conhecimento do PMBOK e certificação PMP."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logger.error(f"Error getting AI response: {str(e)}")
        raise 