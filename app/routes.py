from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from urllib.parse import urlparse
from app import db
from app.models import User, Question, Statistics, TextChunk, Domain
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

# Importar usando caminho relativo
from app.api.openai_client import generate_questions, get_openai_client, generate_topic_summary
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

# Inicializar o gerenciador de banco de dados
db = DatabaseManager()

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
        questions = db.get_all_questions()
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
                client=client,
                api_key=os.getenv('OPENAI_API_KEY'),
                model="gpt-4"
            )
            
            if not questions:
                logger.error("No questions generated")
                return jsonify({'error': 'Failed to generate questions'}), 500
            
            # Update user statistics
            if current_user.is_authenticated:
                with db.get_connection() as conn:
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
    return render_template('model_selection.html')

@main.route('/api/random-question')
@login_required
def api_random_question():
    """Get a random question."""
    try:
        logger.info("[API] Iniciando busca de questão aleatória")
        
        db = DatabaseManager()
        question = db.get_random_question()
        
        if not question:
            logger.warning("[API] Nenhuma questão disponível")
            return jsonify({
                'error': 'Nenhuma questão disponível',
                'details': 'Não há questões no banco de dados ou todas as questões estão inválidas'
            }), 404
        
        # Log para debug
        logger.info(f"[API] Questão retornada: {question}")
        
        # Garantir que todos os campos necessários estejam presentes
        required_fields = ['id', 'question', 'options', 'correct_answer', 'explanation', 'topic']
        for field in required_fields:
            if field not in question or not question[field]:
                logger.error(f"[API] Campo obrigatório ausente ou vazio: {field}")
                return jsonify({
                    'error': f'Questão inválida: campo {field} ausente',
                    'details': 'A questão retornada está incompleta ou mal formatada'
                }), 500
        
        # Garantir que options seja um array
        if not isinstance(question['options'], list):
            logger.error(f"[API] Campo options não é um array: {question['options']}")
            return jsonify({
                'error': 'Questão inválida: campo options mal formatado',
                'details': 'O campo options deve ser um array'
            }), 500
        
        # Garantir que correct_answer seja um número
        if not isinstance(question['correct_answer'], int):
            logger.error(f"[API] Campo correct_answer não é um número: {question['correct_answer']}")
            return jsonify({
                'error': 'Questão inválida: campo correct_answer mal formatado',
                'details': 'O campo correct_answer deve ser um número'
            }), 500
        
        return jsonify(question)
        
    except Exception as e:
        logger.error(f"[API] Erro ao buscar questão aleatória: {str(e)}")
        logger.error("[API] Stack trace:", exc_info=True)
        return jsonify({
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500

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
    
    # Garantir que o índice da resposta correta seja inteiro
    correct_index = int(question['correct_answer'])
    is_correct = (selected_index == correct_index)
    
    logger.info(f"[ANSWER] Questão {question_id}: selecionado={selected_index}, correto={correct_index}, acertou={is_correct}")
    
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
                for line in text.splitlines():
                    match = re.match(r'^(\d+)(?:\.\d+)*-\s*(.*)', line.strip())
                    if match:
                        main_topic = match.group(1)
                        if current_topic is not None and main_topic != current_topic:
                            logger.info(f'[PROCESS-DOCS] Encontrado novo tópico {main_topic} (anterior: {current_topic})')
                            original_blocks.append({'topic': current_topic, 'text': current_block.strip()})
                            current_block = ''
                        current_topic = main_topic
                        current_block += ('' if current_block == '' else '\n') + match.group(2)
                    else:
                        current_block += '\n' + line
                
                if current_block and current_topic is not None:
                    logger.info(f'[PROCESS-DOCS] Adicionando último tópico {current_topic}')
                    original_blocks.append({'topic': current_topic, 'text': current_block.strip()})
                
                logger.info(f'[PROCESS-DOCS] Blocos de texto original extraídos: {len(original_blocks)}')
                for block in original_blocks:
                    logger.info(f'[PROCESS-DOCS] Tópico {block["topic"]}: {len(block["text"])} caracteres')
                
                # Filtrar apenas tópicos com texto não vazio
                original_blocks = [b for b in original_blocks if b['text'].strip()]
                logger.info(f'[PROCESS-DOCS] Tópicos após filtragem: {len(original_blocks)}')
                
                if not original_blocks:
                    logger.error(f'[PROCESS-DOCS] Nenhum tópico válido encontrado no documento {doc_path}')
                    results.append({'name': doc_path, 'status': 'Erro', 'message': 'Nenhum tópico válido encontrado no documento'})
                    continue
                
                # Retornar apenas os tópicos extraídos, sem processamento
                results.append({
                    'name': doc_path, 
                    'status': 'Extraído', 
                    'message': f'Extração concluída com sucesso. {len(original_blocks)} tópicos encontrados.',
                    'topics': original_blocks
                })
                
            except Exception as e:
                current_app.logger.error(f'[PROCESS-DOCS] Erro ao processar documento {doc_path}: {str(e)}')
                results.append({'name': doc_path, 'status': 'Erro', 'message': str(e)})
                continue
                
        logger.info(f'[PROCESS-DOCS] Resultado final da extração: {results}')
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        current_app.logger.error(f'[PROCESS-DOCS] Erro no processamento de documentos: {str(e)}')
        return jsonify({'error': str(e)}), 500

def extract_text_from_pdf(pdf_path):
    logger.info(f'[EXTRACT-PDF] Extraindo texto do arquivo: {pdf_path}')
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            logger.info(f'[EXTRACT-PDF] Total de páginas no PDF: {total_pages}')
            
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if not page_text:
                    logger.warning(f'[EXTRACT-PDF] Página {i+1} retornou texto vazio')
                else:
                    logger.info(f'[EXTRACT-PDF] Página {i+1} extraída ({len(page_text)} caracteres)')
                    text += page_text
                    
            logger.info(f'[EXTRACT-PDF] Extração concluída ({len(text)} caracteres)')
            if not text.strip():
                logger.error('[EXTRACT-PDF] Texto extraído está vazio!')
            return text
    except Exception as e:
        logger.error(f'[EXTRACT-PDF] Erro ao extrair texto do PDF: {str(e)}')
        raise

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
        db = DatabaseManager()
        summaries = db.get_summaries_by_document(document_title)
        
        return jsonify({
            'success': True,
            'chunks': [{
                'id': summary['id'],
                'chunk_text': summary['summary'],
                'processed_text': summary['summary'],
                'created_at': summary['created_at']
            } for summary in summaries]
        })
        
    except Exception as e:
        current_app.logger.error(f'Erro ao buscar chunks do documento {document_title}: {str(e)}')
        return jsonify({'error': str(e)}), 500

@main.route('/api/list-documents', methods=['GET'])
def list_documents():
    uploads_dir = os.path.join('data', 'uploads', 'resumos')
    logger.info(f'[LIST] Listando arquivos em: {uploads_dir}')
    try:
        files = os.listdir(uploads_dir)
        documents = []
        db_manager = DatabaseManager()
        
        for f in files:
            if os.path.isfile(os.path.join(uploads_dir, f)):
                title = os.path.splitext(f)[0]
                processed = False
                
                if current_user.is_authenticated:
                    # Verificar se existem resumos para este documento
                    conn = db_manager.get_connection()
                    cursor = conn.cursor()
                    
                    # Buscar resumos na tabela topic_summaries
                    cursor.execute('''
                        SELECT COUNT(*) 
                        FROM topic_summaries 
                        WHERE document_title = ?
                    ''', (title,))
                    
                    summary_count = cursor.fetchone()[0]
                    conn.close()
                    
                    # Considerar processado se houver pelo menos um resumo
                    processed = summary_count > 0
                    
                    logger.info(f'[LIST] Documento {title}: {summary_count} resumos encontrados')
                
                documents.append({
                    'name': f, 
                    'processed': processed,
                    'summary_count': summary_count if current_user.is_authenticated else 0
                })
                
        logger.info(f'[LIST] Documentos encontrados: {[d["name"] for d in documents]}')
        return jsonify({'documents': documents})
    except Exception as e:
        logger.error(f'[LIST] Erro ao listar documentos: {str(e)}')
        return jsonify({'error': str(e)}), 500

@main.route('/api/upload-document', methods=['POST'])
@login_required
def upload_document():
    uploads_dir = os.path.join('data', 'uploads', 'resumos')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        logger.info(f'[UPLOAD] Diretório criado: {uploads_dir}')
    if 'document' not in request.files:
        current_app.logger.error('[UPLOAD] Nenhum arquivo enviado no upload.')
        return jsonify({'error': 'Nenhum arquivo enviado.'}), 400
    file = request.files['document']
    if file.filename == '':
        current_app.logger.error('[UPLOAD] Nome de arquivo vazio no upload.')
        return jsonify({'error': 'Nome de arquivo vazio.'}), 400
    file_path = os.path.join(uploads_dir, file.filename)
    try:
        file.save(file_path)
        current_app.logger.info(f'[UPLOAD] Arquivo salvo em: {file_path}')
    except Exception as e:
        current_app.logger.error(f'[UPLOAD] Erro ao salvar arquivo: {str(e)}')
        return jsonify({'error': f'Erro ao salvar arquivo: {str(e)}'}), 500
    return jsonify({'success': True, 'filename': file.filename})

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
        document_title = os.path.splitext(filename)[0]
        if current_user.is_authenticated:
            deleted = TextChunk.query.filter_by(document_title=document_title, user_id=current_user.id).delete()
            from app import db
            db.session.commit()
            current_app.logger.info(f'[DELETE] Removidos {deleted} chunks do documento {document_title} para o usuário {current_user.id}')
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

@main.route('/api/process-topic', methods=['POST'])
@login_required
def process_topic():
    """Processa um tópico e gera um resumo"""
    try:
        data = request.get_json()
        document_title = data.get('document_title')
        topic = data.get('topic')
        topic_text = data.get('topic_text')
        
        logger.info(f"[PROCESS-TOPIC] Iniciando processamento de tópico")
        logger.info(f"[PROCESS-TOPIC] Processando tópico {topic} do documento {document_title}")
        
        if not topic_text:
            logger.error("[PROCESS-TOPIC] Texto do tópico não fornecido")
            return jsonify({
                'success': False,
                'message': 'Texto do tópico não fornecido'
            }), 400
        
        # Inicializar cliente OpenAI
        logger.info(f"[PROCESS-TOPIC] Cliente OpenAI inicializado")
        client = get_openai_client()
        
        # Gerar resumo
        logger.info(f"[PROCESS-TOPIC] Gerando resumo para tópico {topic}")
        summary_data = generate_topic_summary(topic_text, client, os.getenv('OPENAI_API_KEY'))
        
        # Salvar no banco de dados
        logger.info(f"[PROCESS-TOPIC] Iniciando salvamento no banco de dados")
        db = DatabaseManager()
        logger.info(f"[PROCESS-TOPIC] DatabaseManager inicializado")
        
        try:
            logger.info(f"[PROCESS-TOPIC] Tentando salvar resumo do tópico")
            logger.info(f"[PROCESS-TOPIC] Dados do resumo: {summary_data}")
            summary_id = db.save_topic_summary(
                document_title=document_title,
                topic=topic,
                summary=summary_data['summary'],
                key_points=summary_data['key_points'],
                practical_examples=summary_data['practical_examples'],
                pmbok_references=summary_data['pmbok_references'],
                domains=summary_data.get('domains', [])  # Usar get() para evitar KeyError
            )
            logger.info(f"[PROCESS-TOPIC] Resumo salvo com ID {summary_id}")
            
            # Buscar o resumo salvo para retornar na resposta
            summary = db.get_topic_summary(summary_id)
            
            return jsonify({
                'success': True,
                'summary_id': summary_id,
                'message': 'Tópico processado com sucesso',
                'summary': summary.summary,
                'key_points': summary.key_points,
                'practical_examples': summary.practical_examples,
                'pmbok_references': summary.pmbok_references,
                'domains': summary.domains
            })
            
        except Exception as e:
            logger.error(f"[PROCESS-TOPIC] Erro ao salvar resumo: {str(e)}")
            logger.error("[PROCESS-TOPIC] Stack trace:", exc_info=True)
            return jsonify({
                'success': False,
                'message': f'Erro ao salvar resumo: {str(e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"[PROCESS-TOPIC] Erro ao processar tópico: {str(e)}")
        logger.error("[PROCESS-TOPIC] Stack trace:", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Erro ao processar tópico: {str(e)}'
        }), 500

@main.route('/api/save-chunks', methods=['POST'])
@login_required
def save_chunks():
    try:
        data = request.get_json()
        document_title = data.get('document')
        chunks = data.get('chunks')
        chunk_text = data.get('chunk_text')
        if not document_title:
            logger.error('[SAVE-CHUNKS] Parâmetro documento ausente')
            return jsonify({'error': 'Parâmetro documento ausente'}), 400
        saved = 0
        # Novo formato: lista de chunks
        if chunks and isinstance(chunks, list):
            for idx, chunk in enumerate(chunks):
                text = chunk.get('chunk_text')
                if not text:
                    logger.warning(f'[SAVE-CHUNKS] Chunk vazio ignorado (idx={idx})')
                    continue
                new_chunk = TextChunk(
                    document_title=document_title,
                    chunk_text=text,
                    processed_text=text,
                    user_id=current_user.id
                )
                db.session.add(new_chunk)
                saved += 1
                logger.info(f'[SAVE-CHUNKS] Chunk salvo (idx={idx}) para documento {document_title} e usuário {current_user.id}')
            db.session.commit()
            logger.info(f'[SAVE-CHUNKS] Total de chunks salvos: {saved}')
            return jsonify({'success': True, 'saved': saved})
        # Compatibilidade: campo antigo
        elif chunk_text:
            new_chunk = TextChunk(
                document_title=document_title,
                chunk_text=chunk_text,
                processed_text=chunk_text,
                user_id=current_user.id
            )
            db.session.add(new_chunk)
            db.session.commit()
            logger.info(f'[SAVE-CHUNKS] Chunk único salvo para documento {document_title} e usuário {current_user.id}')
            return jsonify({'success': True, 'saved': 1})
        else:
            logger.error('[SAVE-CHUNKS] Nenhum chunk fornecido')
            return jsonify({'error': 'Nenhum chunk fornecido'}), 400
    except Exception as e:
        logger.error(f'[SAVE-CHUNKS] Erro ao salvar chunk: {str(e)}')
        return jsonify({'error': str(e)}), 500

@main.route('/api/delete-chunks', methods=['POST'])
@login_required
def delete_chunks():
    try:
        data = request.get_json()
        document_title = data.get('document')
        chunk_id = data.get('chunk_id')
        
        if chunk_id:
            # Excluir chunk específico
            chunk = TextChunk.query.get(chunk_id)
            if not chunk:
                logger.error(f'[DELETE-CHUNKS] Chunk não encontrado: {chunk_id}')
                return jsonify({'error': 'Chunk não encontrado'}), 404
            if chunk.user_id != current_user.id:
                logger.error(f'[DELETE-CHUNKS] Tentativa de excluir chunk de outro usuário: {chunk_id}')
                return jsonify({'error': 'Não autorizado'}), 403
            db.session.delete(chunk)
            db.session.commit()
            logger.info(f'[DELETE-CHUNKS] Chunk {chunk_id} removido')
            return jsonify({'success': True, 'deleted': 1})
        
        # Excluir chunks por documento
        if not document_title:
            logger.error('[DELETE-CHUNKS] Parâmetro documento ausente')
            return jsonify({'error': 'Parâmetro documento ausente'}), 400
        deleted = TextChunk.query.filter_by(document_title=document_title, user_id=current_user.id).delete()
        db.session.commit()
        logger.info(f'[DELETE-CHUNKS] Removidos {deleted} chunks do documento {document_title} para o usuário {current_user.id}')
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        logger.error(f'[DELETE-CHUNKS] Erro ao apagar chunks: {str(e)}')
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
    """Deleta uma questão específica"""
    try:
        db = DatabaseManager()
        if db.delete_question(question_id):
            return jsonify({'success': True, 'message': 'Questão excluída com sucesso'})
        else:
            return jsonify({'success': False, 'error': 'Questão não encontrada'}), 404
    except Exception as e:
        logger.error(f"Erro ao excluir questão {question_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@main.route('/api/domains', methods=['GET'])
@login_required
def get_domains():
    """Retorna a lista de domínios disponíveis"""
    try:
        domains = Domain.query.all()
        return jsonify({
            'success': True,
            'domains': [{'id': d.id, 'name': d.name, 'description': d.description} for d in domains]
        })
    except Exception as e:
        logger.error(f"Erro ao buscar domínios: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@main.route('/api/generate-questions', methods=['POST'])
@login_required
def generate_questions_route():
    try:
        data = request.get_json()
        topic = data.get('topic')
        num_questions = int(data.get('num_questions', 5))  # Default to 5 if not provided
        
        logger.info(f"[GENERATE] Iniciando geração de questões")
        logger.info(f"[GENERATE] Tópico: {topic}")
        logger.info(f"[GENERATE] Número de questões: {num_questions}")
        
        if not topic:
            logger.error("[GENERATE] Tópico não fornecido")
            return jsonify({'error': 'Topic is required'}), 400
            
        if not isinstance(num_questions, int) or num_questions < 1:
            logger.error(f"[GENERATE] Número inválido de questões: {num_questions}")
            return jsonify({'error': 'Number of questions must be a positive integer'}), 400
            
        if not (1 <= num_questions <= 20):
            logger.error(f"[GENERATE] Número de questões fora do intervalo: {num_questions}")
            return jsonify({'error': 'Number of questions must be between 1 and 20'}), 400
            
        logger.info(f"[GENERATE] Gerando {num_questions} questões para o tópico: {topic}")
        
        # Verificar API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("[GENERATE] API key não encontrada")
            return jsonify({'error': 'OpenAI API key not configured'}), 500
        
        # Generate questions using OpenAI
        try:
            questions = generate_questions(
                topic=topic,
                num_questions=num_questions,
                api_key=api_key
            )
            
            if not questions:
                logger.error("[GENERATE] Nenhuma questão gerada")
                return jsonify({'error': 'Failed to generate questions'}), 500
                
            logger.info(f"[GENERATE] Questões geradas: {len(questions)}")
            
            # Salvar questões no banco
            db = DatabaseManager()
            saved_questions = []
            
            for question in questions:
                try:
                    # Validar campos obrigatórios
                    required_fields = ['question', 'options', 'correct_answer', 'explanation', 'topic']
                    missing_fields = [field for field in required_fields if not question.get(field)]
                    
                    if missing_fields:
                        logger.error(f"[GENERATE] Questão com campos ausentes: {missing_fields}")
                        continue
                    
                    # Garantir que options seja um array
                    if not isinstance(question['options'], list):
                        logger.error(f"[GENERATE] Campo options não é um array: {question['options']}")
                        continue
                    
                    # Garantir que correct_answer seja um número
                    if not isinstance(question['correct_answer'], int):
                        logger.error(f"[GENERATE] Campo correct_answer não é um número: {question['correct_answer']}")
                        continue
                    
                    # Salvar questão
                    question_id = db.save_question(question)
                    if question_id:
                        saved_questions.append(question_id)
                        logger.info(f"[GENERATE] Questão salva com ID: {question_id}")
                    
                except Exception as e:
                    logger.error(f"[GENERATE] Erro ao salvar questão: {str(e)}")
                    continue
            
            if not saved_questions:
                logger.error("[GENERATE] Nenhuma questão foi salva")
                return jsonify({'error': 'Failed to save any questions'}), 500
            
            logger.info(f"[GENERATE] Total de questões salvas: {len(saved_questions)}")
            
            return jsonify({
                'success': True,
                'questions': questions,
                'saved_count': len(saved_questions),
                'message': f'Successfully generated and saved {len(saved_questions)} questions'
            })
            
        except Exception as e:
            logger.error(f"[GENERATE] Erro ao gerar questões: {str(e)}")
            logger.error("[GENERATE] Stack trace:", exc_info=True)
            return jsonify({'error': f'Error generating questions: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"[GENERATE] Erro no processamento da requisição: {str(e)}")
        logger.error("[GENERATE] Stack trace:", exc_info=True)
        return jsonify({'error': str(e)}), 500

@main.route('/api/database-status')
@login_required
def api_database_status():
    """Get database status information."""
    try:
        logger.info("[API] Verificando status do banco de dados")
        db = DatabaseManager()
        status = db.check_database_status()
        
        if 'error' in status:
            logger.error(f"[API] Erro ao verificar status do banco: {status['error']}")
            return jsonify({
                'error': 'Erro ao verificar status do banco',
                'details': status['error']
            }), 500
        
        logger.info(f"[API] Status do banco: {status}")
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"[API] Erro ao verificar status do banco: {str(e)}")
        logger.error("[API] Stack trace:", exc_info=True)
        return jsonify({
            'error': 'Erro interno do servidor',
            'details': str(e)
        }), 500 