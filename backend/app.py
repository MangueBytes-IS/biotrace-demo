from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import uuid
import secrets
import tempfile
import io
from pathlib import Path
import sys
import threading
import time
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from ncbi_wrapper import run_collection as run_ncbi_collection, DEMO_SPECIES_LIMIT, DEMO_LIMIT_MESSAGE

load_dotenv()

# Importar ncbi_collector do diretório raiz
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
# Em produção, CORS_ORIGINS=https://seu-site.netlify.app (lista separada por vírgula).
# Sem a variável, aceita qualquer origem (uso local).
CORS(app, origins=[o.strip() for o in os.getenv('CORS_ORIGINS', '*').split(',') if o.strip()])
# Upload de CSV pequeno: 20 espécies cabem com folga em 1 MB
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024

# Configuração (em produção, apontam para o volume persistente)
DATA_FILE = os.getenv('DATA_FILE', 'data.json')
ANALYSES_DIR = os.getenv('ANALYSES_DIR', 'analyses')
MAX_ANALYSES_PER_DAY = 3
MIN_PASSWORD_LENGTH = 8
LOGIN_MAX_FAILURES = 5          # tentativas erradas...
LOGIN_WINDOW_SECONDS = 15 * 60  # ...dentro de 15 minutos bloqueiam novas tentativas do email
login_failures = {}             # email -> instantes das falhas (memória; há um único worker)

# Criar diretórios se não existirem
os.makedirs(ANALYSES_DIR, exist_ok=True)

# ===== UTILITÁRIOS =====

DATA_LOCK = threading.RLock()


def update_analysis(analysis_id, **fields):
    """Atualiza campos de uma análise no data.json"""
    with DATA_LOCK:
        data = load_data()
        for a in data['analyses']:
            if a['id'] == analysis_id:
                a.update(fields)
                break
        save_data(data)


def _species_column(df):
    if df is None or df.empty:
        return []
    col = 'species' if 'species' in df.columns else df.columns[0]
    return sorted({str(s).strip() for s in df[col].dropna() if str(s).strip()})


def build_summary(result_file, species_list):
    """Lê o Excel gerado e monta o resumo exibido na tela de resultados"""
    sheets = pd.read_excel(result_file, sheet_name=None)
    sem_taxid = _species_column(sheets.get('Sem_TaxID'))
    sem_sequencias = _species_column(sheets.get('Sem_Sequencias'))

    with_sequences = 0
    completo = sheets.get('Dados_Completos')
    if completo is not None and 'species' in completo.columns and 'gene' in completo.columns:
        with_sequences = completo[completo['gene'].notna()]['species'].nunique()

    return {
        'total_species': len({s.strip() for s in species_list}),
        'with_sequences': int(with_sequences),
        'without_taxid': len(sem_taxid),
        'without_sequences': len(sem_sequencias),
        'without_taxid_list': sem_taxid,
        'without_sequences_list': sem_sequencias,
        'file_name': os.path.basename(result_file),
        'file_size': os.path.getsize(result_file),
        'sheets': list(sheets.keys()),
    }


def run_analysis_job(analysis_id, species_list, email, dataset_name):
    """Executa a coleta NCBI em background, registrando o progresso"""
    def on_progress(percent, message):
        update_analysis(analysis_id, progress=percent, progress_message=message)

    on_progress(2, 'Iniciando coleta')
    success, result = run_ncbi_collection(
        species_list,
        ANALYSES_DIR,
        email=email,
        dataset_name=dataset_name,
        on_progress=on_progress,
    )

    if not success:
        update_analysis(analysis_id, status='failed', error=result, progress=100, progress_message='Erro')
        return

    try:
        summary = build_summary(result, species_list)
    except Exception as e:
        summary = None
        print(f'Falha ao montar resumo da análise {analysis_id}: {e}')

    update_analysis(
        analysis_id,
        status='completed',
        result_file=result,
        summary=summary,
        progress=100,
        progress_message='Concluída',
    )


def load_data():
    """Carrega dados do arquivo JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'users': {}, 'analyses': []}

def save_data(data):
    """Salva dados no arquivo JSON"""
    # Escrita atômica: a thread da coleta e as requisições leem o mesmo arquivo
    tmp_file = f'{DATA_FILE}.tmp'
    with open(tmp_file, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_file, DATA_FILE)

def get_token():
    """Token de sessão enviado no header Authorization"""
    return request.headers.get('Authorization', '').replace('Bearer ', '').strip()


def get_user_email():
    """Obtém o email da sessão a partir do token"""
    token = get_token()
    if not token:
        return None
    with DATA_LOCK:
        data = load_data()
    return data.get('sessions', {}).get(token)


def read_credentials():
    body = request.get_json(silent=True) or {}
    email = str(body.get('email', '')).strip().lower()
    password = str(body.get('password', ''))
    return email, password


def new_session(data, email):
    token = secrets.token_urlsafe(32)
    data.setdefault('sessions', {})[token] = email
    return token


def too_many_failures(email):
    """Conta as falhas recentes do email; True se já passou do limite."""
    now = time.time()
    recent = [t for t in login_failures.get(email, []) if now - t < LOGIN_WINDOW_SECONDS]
    login_failures[email] = recent
    return len(recent) >= LOGIN_MAX_FAILURES


def count_analyses_today(data, email):
    """Conta análises criadas hoje pelo usuário"""
    today = datetime.now().date()
    return sum(
        1 for a in data['analyses']
        if a['email'] == email and datetime.fromisoformat(a['created_at']).date() == today
    )


def reset_interrupted_jobs():
    """Análises 'processing' de um processo anterior não têm mais thread: marca como falhas.
    Sem isso, uma reinicialização do servidor bloquearia as novas coletas."""
    with DATA_LOCK:
        data = load_data()
        changed = False
        for a in data['analyses']:
            if a.get('status') == 'processing':
                a.update(
                    status='failed',
                    error='Coleta interrompida (o servidor foi reiniciado). Envie o CSV novamente.',
                    progress=100,
                    progress_message='Erro',
                )
                changed = True
        if changed:
            save_data(data)

# ===== ROTAS =====

@app.post('/api/register')
def register():
    """Cria a conta com senha (ou define a senha de uma conta antiga, criada antes da senha existir)"""
    try:
        email, password = read_credentials()
        if not email or '@' not in email:
            return {'error': 'Email inválido'}, 400
        if len(password) < MIN_PASSWORD_LENGTH:
            return {'error': f'A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres'}, 400

        with DATA_LOCK:
            data = load_data()
            data.setdefault('users', {})
            user = data['users'].get(email)
            if user and user.get('password_hash'):
                return {'error': 'Já existe uma conta com este email. Entre com sua senha.'}, 409
            if user is None:
                user = {'created_at': datetime.now().isoformat()}
                data['users'][email] = user
            user['password_hash'] = generate_password_hash(password)
            token = new_session(data, email)
            save_data(data)

        return {'token': token, 'email': email}, 201
    except Exception as e:
        return {'error': str(e)}, 500


@app.post('/api/login')
def login():
    """Login com email e senha; devolve um token de sessão aleatório"""
    try:
        email, password = read_credentials()
        with DATA_LOCK:
            if too_many_failures(email):
                return {'error': 'Muitas tentativas incorretas. Aguarde alguns minutos e tente de novo.'}, 429

            data = load_data()
            user = data.get('users', {}).get(email)
            if not user or not user.get('password_hash') or not check_password_hash(user['password_hash'], password):
                login_failures.setdefault(email, []).append(time.time())
                return {'error': 'Email ou senha inválidos'}, 401

            login_failures.pop(email, None)
            token = new_session(data, email)
            save_data(data)

        return {'token': token, 'email': email}, 200
    except Exception as e:
        return {'error': str(e)}, 500


@app.post('/api/logout')
def logout():
    """Invalida o token de sessão"""
    token = get_token()
    with DATA_LOCK:
        data = load_data()
        data.get('sessions', {}).pop(token, None)
        save_data(data)
    return {'message': 'Sessão encerrada'}, 200

@app.post('/api/analyses')
def create_analysis():
    """Criar nova análise"""
    try:
        email = get_user_email()
        if not email:
            return {'error': 'Não autorizado'}, 401

        # Receber arquivo CSV
        if 'file' not in request.files:
            return {'error': 'Arquivo não enviado'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'error': 'Arquivo vazio'}, 400

        # Ler CSV
        try:
            content = file.read().decode('utf-8')
            species_list = [line.strip() for line in content.split('\n') if line.strip()]

            if not species_list:
                return {'error': 'CSV sem espécies'}, 400

            if len(species_list) > DEMO_SPECIES_LIMIT:
                return {
                    'error': f'{DEMO_LIMIT_MESSAGE} Seu arquivo tem {len(species_list)} espécies.'
                }, 400
        except Exception as e:
            return {'error': f'Erro ao ler CSV: {str(e)}'}, 400

        # Criar análise
        analysis_id = str(uuid.uuid4())
        analysis = {
            'id': analysis_id,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'status': 'processing',
            'species_count': len(species_list),
            'result_file': None,
            'error': None
        }

        analysis['name'] = Path(file.filename).stem
        analysis['progress'] = 0
        analysis['progress_message'] = 'Na fila'
        analysis['summary'] = None

        with DATA_LOCK:
            data = load_data()
            if any(a['status'] == 'processing' for a in data['analyses']):
                return {
                    'error': 'Já existe uma coleta em andamento na versão demo. Aguarde ela terminar e tente de novo.'
                }, 429
            if count_analyses_today(data, email) >= MAX_ANALYSES_PER_DAY:
                return {
                    'error': f'Você atingiu o limite de {MAX_ANALYSES_PER_DAY} análises por dia da versão demo. Tente novamente amanhã.'
                }, 429
            data['analyses'].append(analysis)
            save_data(data)

        # Executar coleta em background; o frontend acompanha via GET /api/analyses/<id>
        threading.Thread(
            target=run_analysis_job,
            args=(analysis_id, species_list, email, analysis['name']),
            daemon=True,
        ).start()

        return {
            'id': analysis_id,
            'status': analysis['status'],
            'message': 'Análise iniciada'
        }, 202

    except Exception as e:
        return {'error': str(e)}, 500

@app.get('/api/analyses')
def list_analyses():
    """Listar análises do usuário"""
    try:
        email = get_user_email()
        if not email:
            return {'error': 'Não autorizado'}, 401

        data = load_data()
        user_analyses = [a for a in data['analyses'] if a['email'] == email]

        return {
            'analyses': sorted(user_analyses, key=lambda x: x['created_at'], reverse=True),
            'today_count': count_analyses_today(data, email),
            'daily_limit': MAX_ANALYSES_PER_DAY,
            'demo_species_limit': DEMO_SPECIES_LIMIT
        }, 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.get('/api/analyses/<analysis_id>')
def get_analysis(analysis_id):
    """Obter detalhes de uma análise"""
    try:
        email = get_user_email()
        if not email:
            return {'error': 'Não autorizado'}, 401

        data = load_data()
        analysis = next((a for a in data['analyses'] if a['id'] == analysis_id and a['email'] == email), None)

        if not analysis:
            return {'error': 'Análise não encontrada'}, 404

        return analysis, 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.get('/api/analyses/<analysis_id>/download')
def download_analysis(analysis_id):
    """Baixar Excel da análise"""
    try:
        email = get_user_email()
        if not email:
            return {'error': 'Não autorizado'}, 401

        data = load_data()
        analysis = next((a for a in data['analyses'] if a['id'] == analysis_id and a['email'] == email), None)

        if not analysis:
            return {'error': 'Análise não encontrada'}, 404

        if analysis['status'] != 'completed' or not analysis['result_file']:
            return {'error': 'Análise não está pronta'}, 400

        result_file = analysis['result_file']
        if not os.path.exists(result_file):
            return {'error': 'Arquivo não encontrado no servidor'}, 404

        return send_file(result_file, as_attachment=True, download_name=f"analise_{analysis_id}.xlsx")
    except Exception as e:
        return {'error': str(e)}, 500

@app.get('/api/health')
def health():
    """Health check"""
    return {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'demo_species_limit': DEMO_SPECIES_LIMIT
    }, 200

# ===== FRONTEND (quando empacotado junto, como na versão demo do Hugging Face) =====

STATIC_DIR = os.getenv('STATIC_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))


@app.get('/')
def serve_index():
    if os.path.isfile(os.path.join(STATIC_DIR, 'index.html')):
        return send_from_directory(STATIC_DIR, 'index.html')
    return {'message': 'API BioTraceX no ar. Frontend não empacotado.'}, 200


@app.get('/<path:path>')
def serve_frontend(path):
    # Rotas /api/* que não existem devem responder JSON, não a página
    if path.startswith('api/'):
        return {'error': 'Rota não encontrada'}, 404
    if os.path.isfile(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    return serve_index()


# ===== INICIALIZAÇÃO =====

reset_interrupted_jobs()

if __name__ == '__main__':
    # debug=False: o depurador do Flask permitiria executar código no servidor
    app.run(debug=False, host='0.0.0.0', port=5000)
