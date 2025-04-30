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
# from .openai_client import generate_questions, generate_questions_with_specialized_models, show_ia_response_with_topics
from app.api.openai_client import generate_questions, generate_questions_with_specialized_models
from .database.db_manager import DatabaseManager
from app.api.openai_client import get_openai_client
from app.openai_client import build_chunk_prompt

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
            client = get_openai_client()
            questions = generate_questions(
                topic=topic,
                num_questions=num_questions,
                client=client,
                api_key=os.getenv('OPENAI_API_KEY'),
                model="gpt-4",
                num_subtopics=num_subtopics
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
                # Separar texto original em blocos por tópico
                # Exemplo: linhas que começam com "1-", "2-", "1.1-", etc.
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
                logger.info(f'[PROCESS-DOCS] Blocos de texto original extraídos: {len(original_blocks)}')
                # Filtrar apenas tópicos com texto não vazio
                original_blocks = [b for b in original_blocks if b['text'].strip()]
                # Remover quebras de linha do texto original para o prompt
                text_no_breaks = text.replace('\n', ' ')
                # Gerar prompt para chunking, agora incluindo o título do documento
                document_title = os.path.splitext(doc_path)[0]
                prompt = build_chunk_prompt(text_no_breaks, document_title=document_title)
                logger.debug(f'[PROCESS-DOCS] Prompt gerado para IA: {prompt[:200]}...')
                # Chamar a IA para processar o texto
                client = get_openai_client()
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Você é um assistente que processa textos técnicos."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                ia_result = response.choices[0].message.content
                logger.info(f'[PROCESS-DOCS] Resposta da IA recebida para {doc_path} (tamanho: {len(ia_result)} caracteres)')
                # Apagar chunks antigos do usuário para este documento
                from app import db
                from app.models import TextChunk
                deleted = TextChunk.query.filter_by(document_title=document_title, user_id=current_user.id).delete()
                logger.info(f'[PROCESS-DOCS] Chunks antigos removidos: {deleted}')
                # Separar por tópicos usando regex (IA)
                topic_blocks = re.split(r'(<T[óo]pico \d+:)', ia_result)
                ia_chunks = []
                i = 1
                while i < len(topic_blocks):
                    header = topic_blocks[i]
                    content = topic_blocks[i+1] if i+1 < len(topic_blocks) else ''
                    ia_chunks.append({'header': header, 'content': content})
                    i += 2
                # Salvar cada chunk separado, associando ao texto original
                chunk_results = []
                ia_topics = set()
                for idx, ia_chunk in enumerate(ia_chunks):
                    match = re.match(r'<T[óo]pico (\d+):', ia_chunk['header'])
                    topic_num = match.group(1) if match else None
                    ia_topics.add(topic_num)
                    original_text = ''
                    for block in original_blocks:
                        if block['topic'] == topic_num:
                            original_text = block['text']
                            break
                    chunk_text = (ia_chunk['header'] + ia_chunk['content']).strip()
                    chunk = TextChunk(
                        document_title=document_title,
                        chunk_text=chunk_text,
                        processed_text=chunk_text,
                        user_id=current_user.id
                    )
                    db.session.add(chunk)
                    logger.info(f'[PROCESS-DOCS] Chunk salvo (tópico {topic_num}) para documento {doc_path} e usuário {current_user.id}')
                    chunk_results.append({
                        'topic': topic_num,
                        'original_text': original_text,
                        'ia_text': chunk_text
                    })
                # Verificar se todos os tópicos do texto original foram analisados
                missing_topics = [block['topic'] for block in original_blocks if block['topic'] not in ia_topics]
                if missing_topics:
                    logger.warning(f'[PROCESS-DOCS] Tópicos não analisados pela IA: {missing_topics}. Reenviando para IA.')
                    for topic in missing_topics:
                        block = next((b for b in original_blocks if b['topic'] == topic), None)
                        if block:
                            # Remover quebras de linha do texto do tópico
                            block_text_no_breaks = block['text'].replace('\n', ' ')
                            prompt_topic = build_chunk_prompt(block_text_no_breaks, document_title=document_title)
                            response_topic = client.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "system", "content": "Você é um assistente que processa textos técnicos."},
                                    {"role": "user", "content": prompt_topic}
                                ],
                                temperature=0.7,
                                max_tokens=1000
                            )
                            ia_topic_result = response_topic.choices[0].message.content
                            logger.info(f'[PROCESS-DOCS] Resposta da IA para tópico {topic} recebida (tamanho: {len(ia_topic_result)} caracteres)')
                            chunk = TextChunk(
                                document_title=document_title,
                                chunk_text=ia_topic_result,
                                processed_text=ia_topic_result,
                                user_id=current_user.id
                            )
                            db.session.add(chunk)
                            chunk_results.append({
                                'topic': topic,
                                'original_text': block['text'].replace('\n', ' '),
                                'ia_text': ia_topic_result
                            })
                db.session.commit()
                results.append({'name': doc_path, 'status': 'Processado', 'message': f'Processamento concluído com sucesso. {len(chunk_results)} tópicos salvos.', 'chunks': chunk_results})
            except Exception as e:
                current_app.logger.error(f'[PROCESS-DOCS] Erro ao processar documento {doc_path}: {str(e)}')
                results.append({'name': doc_path, 'status': 'Erro', 'message': str(e)})
                continue
        logger.info(f'[PROCESS-DOCS] Resultado final do processamento: {results}')
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        current_app.logger.error(f'[PROCESS-DOCS] Erro no processamento de documentos: {str(e)}')
        return jsonify({'error': str(e)}), 500

def extract_text_from_pdf(pdf_path):
    logger.info(f'[EXTRACT-PDF] Extraindo texto do arquivo: {pdf_path}')
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            logger.debug(f'[EXTRACT-PDF] Página extraída ({len(page_text) if page_text else 0} caracteres)')
            text += page_text if page_text else ''
    logger.info(f'[EXTRACT-PDF] Extração concluída ({len(text)} caracteres)')
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

@main.route('/api/list-documents', methods=['GET'])
def list_documents():
    uploads_dir = os.path.join('data', 'uploads', 'resumos')
    logger.info(f'[LIST] Listando arquivos em: {uploads_dir}')
    try:
        files = os.listdir(uploads_dir)
        documents = []
        for f in files:
            if os.path.isfile(os.path.join(uploads_dir, f)):
                title = os.path.splitext(f)[0]
                processed = False
                if current_user.is_authenticated:
                    processed = TextChunk.query.filter_by(document_title=title, user_id=current_user.id).first() is not None
                documents.append({'name': f, 'processed': processed})
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
    try:
        data = request.get_json()
        document_title = data.get('document_title')
        topic = data.get('topic')
        text = data.get('text')
        if not document_title or not topic or not text:
            return jsonify({'error': 'Parâmetros obrigatórios ausentes'}), 400
        # Importações locais corretas
        from app.openai_client import build_chunk_prompt
        from app.api.openai_client import get_openai_client
        prompt = build_chunk_prompt(text, document_title=document_title)
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente que processa textos técnicos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        ia_text = response.choices[0].message.content
        return jsonify({'success': True, 'ia_text': ia_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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