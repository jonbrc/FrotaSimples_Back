# -*- coding: utf-8 -*-
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify

DB_CONFIG = {
    "host" : "localhost",
    "database" : "FrotaSimples",
    "user": "postgres",
    "password" : "123",
    "port" : "5432"
}

app = Flask(__name__)

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        return conn
    except psycopg2.Error as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        return None

## CADASTRO DE USUÁRIOS
@app.route('/usuarios', methods=['POST'])
def criar_usuario():
    data = request.get_json()
    
    if not data or 'nome' not in data or 'email' not in data or 'senha' not in data:
        return jsonify({"erro": "Dados incompletos (nome, email, senha são obrigatórios)"}), 400

    nome = data['nome']
    email = data['email']
    senha_plana = data['senha']
    funcionario_id = data.get('funcionario_id')

    senha_hash = generate_password_hash(senha_plana)

    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503

    try:
        with conn.cursor() as cur: 
            sql = """
                INSERT INTO usuarios (nome, email, senha_hash, funcionario_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """
            params = (nome, email, senha_hash, funcionario_id)
            cur.execute(sql, params)
            
            novo_id = cur.fetchone()[0]
            
            conn.commit() 

            return jsonify({
                "mensagem": "Usuário criado com sucesso",
                "id": novo_id,
                "email": email
            }), 201

    except psycopg2.errors.UniqueViolation:
        conn.rollback() 
        return jsonify({"erro": "O email já está em uso"}), 409
        
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro no banco de dados: {e}") 
        return jsonify({"erro": "Erro interno ao criar usuário."}), 500
        
    finally:
        conn.close()
    
## CRIAÇÃO DE FUNCIONÁRIOS
@app.route('/funcionarios', methods=['POST'])
def criar_funcionario():
    'teste'
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)