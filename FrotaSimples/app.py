import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify

DB_CONFIG = {
    "host" : "localhost",
    "database" : "FrotaSimples",
    "user": "FrotaSimplesDBA",
    "password" : "admin",
    "port" : "5432"
}

app = Flask(__name__)

@app.route('/usuarios',methods=['POST'])
def criar_usuario():
    data = request.get_json()
    if not data or 'nome' not in data or 'email' not in data or 'senha' not in data:
        return jsonify({"erro": "Dados incompletos"}), 400
    else:
        return jsonify({"Mensagem":"Dados completos"}),200
    

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)