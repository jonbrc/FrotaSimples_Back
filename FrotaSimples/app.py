# -*- coding: utf-8 -*-
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify

# Configuração do Banco de Dados
# ATENÇÃO: Adicionado 'client_encoding' para mitigar o erro 'UnicodeDecodeError'
DB_CONFIG = {
    "host": "localhost",
    "database": "FrotaSimples",
    "user": "postgres",
    "password": "123",
    "port": "5432"
}

app = Flask(__name__)

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        # Alterado para uma mensagem de erro sem acentuação para evitar o UnicodeDecodeError
        print(f"DB Connect Fail: {e}") 
        return None

# =============================================================================
# ROTAS DE USUÁRIOS
# =============================================================================

## CADASTRO DE USUÁRIOS (POST)
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

## LISTAR USUÁRIOS (GET)
@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            # ATENÇÃO: Excluindo 'senha_hash' da listagem por segurança.
            cur.execute("SELECT id, nome, email, funcionario_id, criado_em FROM usuarios;")
            
            # Obtém os nomes das colunas
            column_names = [desc[0] for desc in cur.description]
            # Mapeia as linhas para uma lista de dicionários
            usuarios = [dict(zip(column_names, row)) for row in cur.fetchall()]
            
            return jsonify(usuarios), 200

    except psycopg2.Error as e:
        print(f"Erro no banco de dados ao listar usuários: {e}") 
        return jsonify({"erro": "Erro interno ao listar usuários."}), 500
        
    finally:
        conn.close()

# =============================================================================
# ROTAS DE FUNCIONÁRIOS
# =============================================================================

## CADASTRO DE FUNCIONÁRIOS (POST)
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
        return jsonify({"erro": "Erro interno ao cadastrar funcionário."}), 500
        
    finally:
        conn.close()

## LISTAR FUNCIONÁRIOS (GET)
@app.route('/funcionarios', methods=['GET'])
def listar_funcionarios():
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nome, matricula, cargo, criado_em FROM funcionarios;")
            
            column_names = [desc[0] for desc in cur.description]
            funcionarios = [dict(zip(column_names, row)) for row in cur.fetchall()]
            
            return jsonify(funcionarios), 200

    except psycopg2.Error as e:
        print(f"Erro no banco de dados ao listar funcionários: {e}") 
        return jsonify({"erro": "Erro interno ao listar funcionários."}), 500
        
    finally:
        conn.close()

# =============================================================================
# ROTAS DE VEÍCULOS
# =============================================================================

## CADASTRO DE VEÍCULOS (POST)
@app.route('/veiculos', methods=['POST'])
def cadastrar_veiculo():
    data = request.get_json()

    if not data or 'modelo' not in data or 'marca' not in data or 'ano' not in data or 'placa' not in data or 'tipo' not in data:
        return jsonify({"erro": "Dados incompletos (modelo, marca, ano, placa e tipo são obrigatórios)"}), 400
    
    modelo = data['modelo']
    marca = data['marca']
    ano = data['ano']
    placa = data['placa'].upper() 
    tipo = data['tipo']
    
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur: 
            sql = """
                INSERT INTO veiculos (modelo, marca, ano, placa,tipo)
                VALUES (%s, %s, %s, %s,%s)
                RETURNING id;
            """
            params = (modelo, marca, ano, placa,tipo)
            cur.execute(sql, params)
            
            novo_id = cur.fetchone()[0]
            
            conn.commit() 

            return jsonify({
                "mensagem": "Veículo cadastrado com sucesso",
                "id": novo_id,
                "placa": placa,
                "tipo" : tipo
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

## LISTAR VEÍCULOS (GET)
@app.route('/veiculos', methods=['GET'])
def listar_veiculos():
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, modelo, marca, ano, placa,tipo, ativo, criado_em FROM veiculos;")
            
            column_names = [desc[0] for desc in cur.description]
            veiculos = [dict(zip(column_names, row)) for row in cur.fetchall()]
            
            return jsonify(veiculos), 200

    except psycopg2.Error as e:
        print(f"Erro no banco de dados ao listar veículos: {e}") 
        return jsonify({"erro": "Erro interno ao listar veículos."}), 500
        
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)