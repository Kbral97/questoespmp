#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para fazer dump do banco de dados SQLite.
"""

import sqlite3
import os
from datetime import datetime

def dump_database():
    """Faz o dump do banco de dados para um arquivo SQL."""
    try:
        # Caminho do banco de dados
        db_path = 'instance/questoespmp.db'
        
        # Verificar se o banco existe
        if not os.path.exists(db_path):
            print(f"Erro: Banco de dados não encontrado em {db_path}")
            return False
            
        # Conectar ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Nome do arquivo de saída
        output_file = 'db_dump.sql'
        
        # Abrir arquivo para escrita
        with open(output_file, 'w', encoding='utf-8') as f:
            # Escrever cabeçalho
            f.write('-- Dump do banco de dados questoespmp.db\n')
            f.write('-- Gerado em: ' + str(datetime.now()) + '\n\n')
            
            # Obter todas as tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Para cada tabela
            for table in tables:
                table_name = table[0]
                
                # Pular tabelas do sistema
                if table_name.startswith('sqlite_'):
                    continue
                    
                # Obter estrutura da tabela
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                # Obter dados da tabela
                cursor.execute(f"SELECT * FROM {table_name};")
                rows = cursor.fetchall()
                
                # Escrever estrutura da tabela
                f.write(f'\n-- Estrutura da tabela {table_name}\n')
                f.write(f'CREATE TABLE IF NOT EXISTS {table_name} (\n')
                
                # Escrever colunas
                column_defs = []
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    col_notnull = 'NOT NULL' if col[3] else ''
                    col_default = f"DEFAULT {col[4]}" if col[4] is not None else ''
                    col_pk = 'PRIMARY KEY' if col[5] else ''
                    
                    column_def = f"    {col_name} {col_type} {col_notnull} {col_default} {col_pk}"
                    column_defs.append(column_def.strip())
                
                f.write(',\n'.join(column_defs))
                f.write('\n);\n\n')
                
                # Escrever dados
                if rows:
                    f.write(f'-- Dados da tabela {table_name}\n')
                    for row in rows:
                        values = []
                        for value in row:
                            if value is None:
                                values.append('NULL')
                            elif isinstance(value, str):
                                # Escapar aspas simples
                                escaped_value = value.replace("'", "''")
                                values.append(f"'{escaped_value}'")
                            else:
                                values.append(str(value))
                        
                        f.write(f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n")
                    f.write('\n')
        
        print(f"Dump do banco de dados concluído com sucesso em {output_file}")
        return True
        
    except Exception as e:
        print(f"Erro ao fazer dump do banco de dados: {str(e)}")
        return False

if __name__ == '__main__':
    dump_database()