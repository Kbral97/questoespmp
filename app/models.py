from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.database.db_manager import DatabaseManager
import logging

# Criar instância do DatabaseManager
db_manager = DatabaseManager()

# Configurar o logger
logger = logging.getLogger(__name__)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    questions = db.relationship('Question', backref='author', lazy=True)
    statistics = db.relationship('Statistics', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    domain = db.Column(db.String(50), nullable=False)
    process_group = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Statistics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_questions = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    incorrect_answers = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class TextChunk(db.Model):
    __tablename__ = 'text_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    document_title = db.Column(db.String(255), nullable=False)
    chunk_text = db.Column(db.Text, nullable=False)
    processed_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('text_chunks', lazy=True))

    def __repr__(self):
        return f'<TextChunk {self.id} - {self.document_title}>'

class Domain(db.Model):
    __tablename__ = 'domains'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Domain {self.name}>'

class AIModel(db.Model):
    __tablename__ = 'ai_models'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # 'question', 'answer', 'distractor'
    model_id = db.Column(db.String(100), nullable=False)  # ID do modelo fine-tuned
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<AIModel {self.name} ({self.model_type})>'

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    topics = db.relationship('Topic', backref='document', lazy=True)
    
    def __repr__(self):
        return f'<Document {self.title}>'

class Topic(db.Model):
    __tablename__ = 'topics'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    summaries = db.relationship('Summary', backref='topic', lazy=True)
    
    def __repr__(self):
        return f'<Topic {self.number} - {self.title}>'

class Summary(db.Model):
    __tablename__ = 'summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    key_points = db.Column(db.Text)
    practical_examples = db.Column(db.Text)
    pmbok_references = db.Column(db.Text)
    related_domains = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Summary {self.id} for Topic {self.topic_id}>'

class TopicSummary(db.Model):
    __tablename__ = 'topic_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    document_title = db.Column(db.String(255), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text)
    key_points = db.Column(db.Text)
    practical_examples = db.Column(db.Text)
    pmbok_references = db.Column(db.Text)
    domains = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TopicSummary {self.topic}>'

def init_db():
    """Inicializa o banco de dados criando as tabelas necessárias."""
    try:
        logger.info("Iniciando inicialização do banco de dados...")
        
        # Criar todas as tabelas
        db.create_all()
        logger.info("Tabelas do banco de dados criadas com sucesso.")
        
        # Inicializar domínios padrão
        from app.database import init_default_domains
        init_default_domains()
        
        logger.info("Banco de dados inicializado com sucesso.")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        raise e
        
def get_db():
    return db_manager.get_connection() 