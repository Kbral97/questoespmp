# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
.\venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
$env:FLASK_APP = "app"
$env:FLASK_ENV = "development"

# Inicializar banco de dados
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Executar aplicação
flask run 