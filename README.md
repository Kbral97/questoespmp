# QuestoesPMP

Sistema de geração e gerenciamento de questões para certificação PMP (Project Management Professional).

## Descrição

O QuestoesPMP é uma aplicação web desenvolvida em Flask que permite:
- Geração de questões para certificação PMP usando IA
- Gerenciamento de questões e estatísticas
- Treinamento de modelos personalizados
- Interface web moderna e responsiva

## Requisitos

- Python 3.8+
- Flask
- SQLAlchemy
- OpenAI API
- Outras dependências listadas em `requirements.txt`

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/questoespmp.git
cd questoespmp
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. Inicialize o banco de dados:
```bash
flask db upgrade
```

## Uso

1. Inicie o servidor de desenvolvimento:
```bash
flask run
```

2. Acesse a aplicação em `http://localhost:5000`

## Estrutura do Projeto

```
questoespmp/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── forms.py
│   └── templates/
├── src/
│   └── questoespmp2/
│       ├── api/
│       ├── database/
│       └── __init__.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes. 