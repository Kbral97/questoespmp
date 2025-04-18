from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from app.models import User, Question, Statistics
import json
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import ChangePasswordForm
import sys
import os
from dotenv import load_dotenv, set_key
from pathlib import Path
from datetime import datetime
import logging

# Importar usando caminho relativo
from .api.openai_client import generate_questions, generate_questions_with_specialized_models
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
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == password:  # Em produção, use hashing adequado
            login_user(user)
            return redirect(url_for('main.index'))
        flash('Usuário ou senha inválidos')
    return render_template('login.html')

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
def settings():
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
        return redirect(url_for('main.settings'))

    return render_template('settings.html', 
                         openai_api_key=openai_api_key,
                         other_api_key=other_api_key)

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