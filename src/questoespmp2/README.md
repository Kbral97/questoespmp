# PMP Questions Generator - Refactored

Este é o código refatorado do Gerador de Questões para Certificação PMP. A estrutura foi reorganizada para facilitar a manutenção e expansão do projeto.

## Estrutura do Projeto

```
questoespmp2_refactored/
├── __init__.py         # Inicialização do pacote
├── __main__.py         # Ponto de entrada da aplicação
├── app.py              # Classe principal do aplicativo
├── api/                # Módulos para integração com APIs
│   ├── __init__.py
│   └── openai_client.py
├── database/           # Módulos para operações de banco de dados
│   ├── __init__.py
│   └── db_manager.py
├── screens/            # Telas da interface do usuário
│   ├── __init__.py
│   ├── home_screen.py
│   ├── api_config_screen.py
│   ├── generate_questions_screen.py
│   ├── answer_question_screen.py
│   ├── filter_questions_screen.py
│   ├── statistics_screen.py
│   └── batch_generate_screen.py
└── utils/              # Utilitários e funções auxiliares
    ├── __init__.py
    └── file_utils.py
```

## Como Utilizar

1. **Instalar dependências:**
   ```
   pip install kivymd openai python-dotenv
   ```

2. **Executar a aplicação:**
   ```
   python -m questoespmp2_refactored
   ```

## Benefícios da Nova Estrutura

1. **Separação por Funcionalidade**: Cada módulo tem uma responsabilidade clara, facilitando a manutenção.

2. **Melhor Organização**: Screens, banco de dados e utilitários estão em diretórios separados.

3. **Maior Legibilidade**: Arquivos menores são mais fáceis de entender.

4. **Reutilização de Código**: Funções utilitárias são centralizadas.

5. **Manutenção Simplificada**: Encontrar e corrigir bugs é mais simples.

## Principais Implementações

- **App.py**: Configura e inicializa o aplicativo principal
- **Screens**: Interface do usuário para cada funcionalidade
- **Database**: Gerenciamento da base de dados das questões
- **API**: Integração com OpenAI para geração de questões
- **Utils**: Funções utilitárias para manipulação de arquivos

## Comparação com a Versão Anterior

A versão anterior tinha todos os componentes em um único arquivo `app.py` gigante com mais de 70.000 linhas. A nova estrutura divide esse arquivo em módulos separados e organizados, o que torna o código:

- Mais fácil de entender
- Mais fácil de modificar
- Mais fácil de testar
- Mais fácil de expandir

## Como Estender

Para adicionar novos recursos:

1. Crie novos módulos na pasta apropriada (screens, utils, etc.)
2. Importe-os onde necessário
3. Atualize app.py se precisar adicionar novas telas ao screen manager

## Notas de Desenvolvimento

- Foram corrigidos problemas de sintaxe e indentação
- O método `go_back` da classe BatchGenerateScreen agora usa `MDApp.get_running_app()` em vez de `self.app`
- Foram adicionadas todas as telas necessárias ao screen manager
- O atributo cursor foi adicionado à classe QuestionsGeneratorApp 