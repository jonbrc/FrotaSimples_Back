# -*- coding: utf-8 -*-
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify
from flask_cors import CORS

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
CORS(app, resources={r"/*": {"origins": "http://localhost:4200"}})

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

## LOGIN DE USUÁRIOS (POST)
@app.route('/login', methods=['POST'])
def login_usuario():
    data = request.get_json()

    # 1. Validação de campos
    if not data or 'email' not in data or 'senha' not in data:
        return jsonify({"erro": "Email e senha são obrigatórios"}), 400
    
    email = data['email']
    senha_plana = data['senha']
    
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503

    try:
        with conn.cursor() as cur:
            # 2. Busca o hash da senha e outros dados importantes pelo email
            sql = """
                SELECT id, nome, email, senha_hash, funcionario_id 
                FROM usuarios 
                WHERE email = %s;
            """
            cur.execute(sql, (email,))
            user_record = cur.fetchone()

            if user_record:
                # 3. Mapeia o registro para um dicionário
                column_names = [desc[0] for desc in cur.description]
                user_data = dict(zip(column_names, user_record))
                
                # 4. Verifica a senha
                if check_password_hash(user_data['senha_hash'], senha_plana):
                    # Autenticação bem-sucedida
                    
                    # 5. Remove o hash da resposta por segurança
                    del user_data['senha_hash'] 
                    
                    return jsonify({
                        "mensagem": "Login bem-sucedido",
                        "usuario": user_data
                    }), 200
                else:
                    # Senha incorreta
                    return jsonify({"erro": "Email ou senha incorretos"}), 401
            else:
                # Usuário não encontrado
                return jsonify({"erro": "Email ou senha incorretos"}), 401

    except psycopg2.Error as e:
        print(f"Erro no banco de dados durante o login: {e}") 
        return jsonify({"erro": "Erro interno ao tentar login."}), 500
        
    finally:
        conn.close()

## ATUALIZAR SENHA DO USUÁRIO (PUT)
@app.route('/usuarios/<int:usuario_id>/senha', methods=['PUT'])
def atualizar_senha_usuario(usuario_id):
    data = request.get_json()

    # 1. Validação básica
    if not data or 'nova_senha' not in data:
        return jsonify({"erro": "A nova senha é obrigatória"}), 400

    senha_atual = data.get('senha_atual')  # opcional
    nova_senha = data['nova_senha']

    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503

    try:
        with conn.cursor() as cur:
            # 2. Busca o hash atual
            cur.execute(
                "SELECT senha_hash FROM usuarios WHERE id = %s;",
                (usuario_id,)
            )
            result = cur.fetchone()

            if not result:
                return jsonify({"erro": "Usuário não encontrado"}), 404

            senha_hash_atual = result[0]

            # 3. Se senha atual foi enviada, valida
            if senha_atual:
                if not check_password_hash(senha_hash_atual, senha_atual):
                    return jsonify({"erro": "Senha atual incorreta"}), 401

            # 4. Gera novo hash
            nova_senha_hash = generate_password_hash(nova_senha)

            # 5. Atualiza no banco
            cur.execute(
                """
                UPDATE usuarios
                SET senha_hash = %s
                WHERE id = %s;
                """,
                (nova_senha_hash, usuario_id)
            )

            conn.commit()

            return jsonify({
                "mensagem": "Senha atualizada com sucesso"
            }), 200

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro ao atualizar senha: {e}")
        return jsonify({"erro": "Erro interno ao atualizar senha"}), 500

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

## ATUALIZAR STATUS DO VEÍCULO (PATCH)
@app.route('/veiculos/<int:veiculo_id>/status', methods=['PATCH'])
def atualizar_status_veiculo(veiculo_id):
    """
    Atualiza o status (ativo/inativo) de um veículo.
    Útil para marcar veículo como emprestado (ativo=False) ou disponível (ativo=True)
    """
    data = request.get_json()
    
    if not data or 'ativo' not in data:
        return jsonify({"erro": "Campo 'ativo' é obrigatório (true ou false)"}), 400
    
    ativo = data['ativo']
    
    # Validação do tipo booleano
    if not isinstance(ativo, bool):
        return jsonify({"erro": "O campo 'ativo' deve ser um booleano (true ou false)"}), 400
    
    conn = get_db_connection()
    
    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            # Verifica se o veículo existe
            cur.execute("SELECT id, modelo, placa FROM veiculos WHERE id = %s;", (veiculo_id,))
            veiculo = cur.fetchone()
            
            if not veiculo:
                return jsonify({"erro": f"Veículo com ID {veiculo_id} não encontrado"}), 404
            
            # Atualiza o status
            sql = """
                UPDATE veiculos 
                SET ativo = %s 
                WHERE id = %s
                RETURNING id, modelo, marca, ano, placa, tipo, ativo;
            """
            cur.execute(sql, (ativo, veiculo_id))
            
            updated_row = cur.fetchone()
            column_names = [desc[0] for desc in cur.description]
            veiculo_atualizado = dict(zip(column_names, updated_row))
            
            conn.commit()
            
            status_texto = "disponível" if ativo else "indisponível"
            
            return jsonify({
                "mensagem": f"Status do veículo atualizado para {status_texto}",
                "veiculo": veiculo_atualizado
            }), 200
    
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro no banco de dados ao atualizar status: {e}")
        return jsonify({"erro": "Erro interno ao atualizar status do veículo."}), 500
    
    finally:
        conn.close()

## BUSCAR VEÍCULOS DISPONÍVEIS (GET)
@app.route('/veiculos/disponiveis', methods=['GET'])
def listar_veiculos_disponiveis():
    """
    Lista apenas os veículos que estão disponíveis (ativo = TRUE).
    Útil para exibir opções de veículos disponíveis para empréstimo.
    """
    conn = get_db_connection()
    
    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT id, modelo, marca, ano, placa, tipo, criado_em
                FROM veiculos
                WHERE ativo = TRUE
                ORDER BY modelo, marca;
            """
            cur.execute(sql)
            
            column_names = [desc[0] for desc in cur.description]
            veiculos_disponiveis = [dict(zip(column_names, row)) for row in cur.fetchall()]
            
            return jsonify({
                "total": len(veiculos_disponiveis),
                "veiculos": veiculos_disponiveis
            }), 200
    
    except psycopg2.Error as e:
        print(f"Erro no banco de dados ao listar veículos disponíveis: {e}")
        return jsonify({"erro": "Erro interno ao listar veículos disponíveis."}), 500
    
    finally:
        conn.close()


# =============================================================================
# ROTAS DE EMPRÉSTIMOS
# =============================================================================

## REGISTRAR EMPRÉSTIMO (POST)
@app.route('/emprestimos', methods=['POST'])
def registrar_emprestimo():
    data = request.get_json()

    # Validação de campos obrigatórios para o registro de saída
    required_fields = ['veiculo_id', 'funcionario_id', 'data_saida', 'km_saida']
    if not all(field in data for field in required_fields):
        return jsonify({"erro": f"Dados incompletos. Campos obrigatórios: {', '.join(required_fields)}"}), 400
    
    veiculo_id = data['veiculo_id']
    funcionario_id = data['funcionario_id']
    data_saida = data['data_saida']
    km_saida = data['km_saida']
    
    # Campos opcionais
    data_retorno = data.get('data_retorno') # Deve ser NULL em uma saída inicial
    km_retorno = data.get('km_retorno')     # Deve ser NULL em uma saída inicial
    observacao = data.get('observacao')
    
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur: 
            sql = """
                INSERT INTO emprestimos (veiculo_id, funcionario_id, data_saida, km_saida, observacao)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """
            params = (veiculo_id, funcionario_id, data_saida, km_saida, observacao)
            cur.execute(sql, params)
            
            novo_id = cur.fetchone()[0]
            
            conn.commit() 

            return jsonify({
                "mensagem": "Empréstimo (Saída) registrado com sucesso",
                "id": novo_id,
                "veiculo_id": veiculo_id,
                "funcionario_id": funcionario_id
            }), 201
    
    except psycopg2.errors.ForeignKeyViolation as e:
        # Erro de chave estrangeira (veículo ou funcionário não existe)
        conn.rollback() 
        print(f"Erro de chave estrangeira: {e}") 
        return jsonify({"erro": "ID de veículo ou funcionário inválido."}), 404

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro no banco de dados ao registrar empréstimo: {e}") 
        return jsonify({"erro": "Erro interno ao registrar empréstimo."}), 500
        
    finally:
        conn.close()

## LISTAR EMPRÉSTIMOS (GET)
@app.route('/emprestimos', methods=['GET'])
def listar_emprestimos():
    conn = get_db_connection()

    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            # Seleciona todos os campos de empréstimos
            sql = """
                SELECT 
                    e.id, 
                    e.veiculo_id, 
                    v.placa AS veiculo_placa,
                    e.funcionario_id, 
                    f.nome AS funcionario_nome,
                    e.data_saida, 
                    e.km_saida, 
                    e.data_retorno, 
                    e.km_retorno, 
                    e.observacao, 
                    e.criado_em
                FROM emprestimos e
                JOIN veiculos v ON e.veiculo_id = v.id
                JOIN funcionarios f ON e.funcionario_id = f.id
                ORDER BY e.data_saida DESC;
            """
            cur.execute(sql)
            
            column_names = [desc[0] for desc in cur.description]
            emprestimos = [dict(zip(column_names, row)) for row in cur.fetchall()]
            
            return jsonify(emprestimos), 200

    except psycopg2.Error as e:
        print(f"Erro no banco de dados ao listar empréstimos: {e}") 
        return jsonify({"erro": "Erro interno ao listar empréstimos."}), 500
        
    finally:
        conn.close()

## FINALIZAR EMPRÉSTIMO (PATCH)
@app.route('/emprestimos/<int:emprestimo_id>/finalizar', methods=['PATCH'])
def finalizar_emprestimo(emprestimo_id):
    """
    Finaliza um empréstimo registrando a data de retorno e km de retorno.
    Também atualiza o status do veículo para disponível (ativo=True).
    """
    data = request.get_json()
    
    # Validação de campos obrigatórios
    if not data or 'data_retorno' not in data or 'km_retorno' not in data:
        return jsonify({"erro": "Dados incompletos (data_retorno e km_retorno são obrigatórios)"}), 400
    
    data_retorno = data['data_retorno']
    km_retorno = data['km_retorno']
    observacao_adicional = data.get('observacao')
    
    conn = get_db_connection()
    
    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            # Busca o empréstimo e verifica se existe
            sql_select = """
                SELECT id, veiculo_id, funcionario_id, data_saida, km_saida, 
                       data_retorno, km_retorno, observacao
                FROM emprestimos 
                WHERE id = %s;
            """
            cur.execute(sql_select, (emprestimo_id,))
            emprestimo = cur.fetchone()
            
            if not emprestimo:
                return jsonify({"erro": f"Empréstimo com ID {emprestimo_id} não encontrado"}), 404
            
            # Mapeia o resultado
            column_names = [desc[0] for desc in cur.description]
            emprestimo_data = dict(zip(column_names, emprestimo))
            
            # Verifica se o empréstimo já foi finalizado
            if emprestimo_data['data_retorno'] is not None:
                return jsonify({
                    "erro": "Este empréstimo já foi finalizado",
                    "data_retorno_anterior": str(emprestimo_data['data_retorno'])
                }), 400
            
            # Validação: km_retorno deve ser maior ou igual a km_saida
            if float(km_retorno) < float(emprestimo_data['km_saida']):
                return jsonify({
                    "erro": "A quilometragem de retorno não pode ser menor que a quilometragem de saída",
                    "km_saida": str(emprestimo_data['km_saida']),
                    "km_retorno_informado": str(km_retorno)
                }), 400
            
            # Monta a observação final (concatena se já existir uma)
            observacao_final = emprestimo_data['observacao']
            if observacao_adicional:
                if observacao_final:
                    observacao_final = f"{observacao_final} | Retorno: {observacao_adicional}"
                else:
                    observacao_final = f"Retorno: {observacao_adicional}"
            
            # Atualiza o empréstimo com os dados de retorno
            sql_update_emprestimo = """
                UPDATE emprestimos 
                SET data_retorno = %s, 
                    km_retorno = %s,
                    observacao = %s
                WHERE id = %s
                RETURNING id, veiculo_id, funcionario_id, data_saida, km_saida, 
                          data_retorno, km_retorno, observacao;
            """
            cur.execute(sql_update_emprestimo, (data_retorno, km_retorno, observacao_final, emprestimo_id))
            
            updated_row = cur.fetchone()
            column_names = [desc[0] for desc in cur.description]
            emprestimo_finalizado = dict(zip(column_names, updated_row))
            
            # Atualiza o status do veículo para disponível (ativo = True)
            veiculo_id = emprestimo_finalizado['veiculo_id']
            sql_update_veiculo = """
                UPDATE veiculos 
                SET ativo = TRUE 
                WHERE id = %s;
            """
            cur.execute(sql_update_veiculo, (veiculo_id,))
            
            conn.commit()
            
            # Calcula a distância percorrida
            distancia_percorrida = float(km_retorno) - float(emprestimo_data['km_saida'])
            
            return jsonify({
                "mensagem": "Empréstimo finalizado com sucesso",
                "emprestimo": emprestimo_finalizado,
                "distancia_percorrida_km": round(distancia_percorrida, 2),
                "veiculo_disponivel": True
            }), 200
    
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Erro no banco de dados ao finalizar empréstimo: {e}")
        return jsonify({"erro": "Erro interno ao finalizar empréstimo."}), 500
    
    finally:
        conn.close()

## BUSCAR EMPRÉSTIMOS ATIVOS (GET)
@app.route('/emprestimos/ativos', methods=['GET'])
def listar_emprestimos_ativos():
    """
    Lista apenas os empréstimos que ainda não foram finalizados (data_retorno = NULL).
    Útil para visualizar quais veículos estão emprestados no momento.
    """
    conn = get_db_connection()
    
    if conn is None:
        return jsonify({"erro": "Falha na conexão com o banco de dados"}), 503
    
    try:
        with conn.cursor() as cur:
            sql = """
                SELECT 
                    e.id, 
                    e.veiculo_id, 
                    v.placa AS veiculo_placa,
                    v.modelo AS veiculo_modelo,
                    v.marca AS veiculo_marca,
                    e.funcionario_id, 
                    f.nome AS funcionario_nome,
                    e.data_saida, 
                    e.km_saida, 
                    e.observacao, 
                    e.criado_em
                FROM emprestimos e
                JOIN veiculos v ON e.veiculo_id = v.id
                JOIN funcionarios f ON e.funcionario_id = f.id
                WHERE e.data_retorno IS NULL
                ORDER BY e.data_saida DESC;
            """
            cur.execute(sql)
            
            column_names = [desc[0] for desc in cur.description]
            emprestimos_ativos = [dict(zip(column_names, row)) for row in cur.fetchall()]
            
            return jsonify({
                "total": len(emprestimos_ativos),
                "emprestimos": emprestimos_ativos
            }), 200
    
    except psycopg2.Error as e:
        print(f"Erro no banco de dados ao listar empréstimos ativos: {e}")
        return jsonify({"erro": "Erro interno ao listar empréstimos ativos."}), 500
    
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)