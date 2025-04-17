from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from app.models import User, Question, Statistics
import json
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import ChangePasswordForm
import sys
import os
from dotenv import load_dotenv

# Adicionar o diretório src ao PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Importar usando caminho absoluto
from questoespmp2.api.openai_client import generate_questions
from questoespmp2.database.db_manager import DatabaseManager
import logging

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
    try:
        # Verificar se a API key está configurada
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({'error': 'API key não configurada'}), 500

        data = request.get_json()
        topic = data.get('topic')
        num_questions = data.get('num_questions')

        if not topic or not num_questions:
            return jsonify({'error': 'Tópico e número de questões são obrigatórios'}), 400

        # Gerar questões usando a implementação existente
        questions = generate_questions(
            topic=topic,
            num_questions=num_questions,
            api_key=api_key,
            progress_callback=lambda progress, message: logging.info(f"Progresso: {progress}% - {message}")
        )

        if not questions:
            return jsonify({'error': 'Não foi possível gerar questões'}), 500

        # Salvar questões no banco de dados
        for question_data in questions:
            question = Question(
                content=question_data['question'],
                answer=question_data['correct_answer'],
                domain=topic,
                process_group='',  # Pode ser preenchido posteriormente
                user_id=current_user.id
            )
            db.session.add(question)

        # Atualizar estatísticas
        stats = Statistics.query.filter_by(user_id=current_user.id).first()
        if not stats:
            stats = Statistics(user_id=current_user.id)
            db.session.add(stats)
        
        stats.total_questions += len(questions)
        db.session.commit()

        return jsonify({
            'success': True,
            'questions': questions
        })

    except Exception as e:
        logging.error(f'Erro ao gerar questões: {str(e)}')
        db.session.rollback()
        return jsonify({'error': 'Erro ao gerar questões'}), 500

@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('main.settings'))
        else:
            flash('Senha atual incorreta.', 'error')
    return render_template('settings.html', form=form)

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