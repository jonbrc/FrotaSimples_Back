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
    
## CADASTRO DE FUNCIONÁRIOS
@app.route('/funcionarios', methods=['POST'])
def criar_funcionario():
    
    data = request.get_json()
    if not data or 'nome' not in data or 'matricula' not in data or 'cargo' not in data:
         return jsonify({"erro": "Dados incompletos (nome, matricula, cargo)"}), 400
    
    nome = data['nome']
    matricula = data['matricula']
    cargo = data['cargo']
    
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur: 
            sql = """
                INSERT INTO funcionarios (nome, matricula, cargo)
                VALUES (%s, %s, %s)
                RETURNING id;
            """
            params = (nome, matricula, cargo)
            cur.execute(sql, params)
            
            novo_id = cur.fetchone()[0]
            
            conn.commit() 

            return jsonify({
                "mensagem": "Funcionário cadastrado com sucesso",
                "id": novo_id,
                "nome": nome
            }), 201

    except psycopg2.errors.UniqueViolation:
        conn.rollback() 
        return jsonify({"erro": "A matrícula já está em uso"}), 409
        
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro no banco de dados: {e}") 
        return jsonify({"erro": "Erro interno ao criar usuário."}), 500
        
    finally:
        conn.close()

## CADASTRO DE VEÍCULOS
@app.route('/veiculos', methods=['POST'])
def cadastrar_veiculo():
    data = request.get_json()

    if not data or 'modelo' not in data or 'marca' not in data or 'ano' not in data or 'placa' not in data:
        return jsonify({"erro": "Dados incompletos (modelo, marca, ano, placa são obrigatórios)"}), 400
    
    modelo = data['modelo']
    marca = data['marca']
    ano = data['ano']
    placa = data['placa'].upper() 
    
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur: 
            sql = """
                INSERT INTO veiculos (modelo, marca, ano, placa)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """
            params = (modelo, marca, ano, placa)
            cur.execute(sql, params)
            
            novo_id = cur.fetchone()[0]
            
            conn.commit() 

            return jsonify({
                "mensagem": "Veículo cadastrado com sucesso",
                "id": novo_id,
                "placa": placa
            }), 201

    except psycopg2.errors.UniqueViolation:
        conn.rollback() 
        return jsonify({"erro": "A placa já está em uso"}), 409
    
    except psycopg2.errors.CheckViolation as e:
        conn.rollback() 
        return jsonify({"erro": "O ano do veículo não é válido (deve ser >= 1900)"}), 400
        
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro no banco de dados: {e}") 
        return jsonify({"erro": "Erro interno ao cadastrar veículo."}), 500
    
    finally:
        conn.close()
    
 
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)