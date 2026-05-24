import os
import json
from flask import Flask, send_from_directory, request, jsonify
from urllib import request as urlrequest
from urllib import parse as urlparse
from urllib.error import HTTPError, URLError
try:
    import requests as pyrequests
except Exception:
    pyrequests = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Servir arquivos estáticos sem conflitar com rotas /api
# Usar caminho '/static' evita que o roteamento de estáticos intercepte '/api/*'
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='/static')

@app.route('/')
def root():
    # Em modo teste, apenas retorna OK para validar subida do servidor
    if request.args.get('test') == 'true':
        return jsonify(status='ok'), 200
    return send_from_directory(BASE_DIR, 'index.html')

# Rota alternativa para acessar diretamente /index.html
@app.route('/index.html')
def index_html():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/login')
def login_page():
    return send_from_directory(BASE_DIR, 'login.html')

# Rota alternativa para acessar diretamente /login.html
@app.route('/login.html')
def login_html():
    return send_from_directory(BASE_DIR, 'login.html')

# Endpoint de autenticação: encaminha credenciais para a API FastAPI
@app.post('/login')
def do_login():
    try:
        payload = request.get_json(silent=True) or {}
        email = payload.get('email')
        password = payload.get('password')
        if not email or not password:
            return jsonify(success=False, message='Email e senha são obrigatórios.'), 400

        # A API FastAPI espera dados form-urlencoded com campos 'username' e 'password'
        api_url = 'http://127.0.0.1:8000/login'
        form_payload = {'username': email, 'password': password}

        # Primeiro tenta via requests (se disponível), senão usa urllib
        if pyrequests is not None:
            try:
                resp = pyrequests.post(api_url, data=form_payload, timeout=10)
                if resp.status_code >= 200 and resp.status_code < 300:
                    data = resp.json()
                    return jsonify(success=True, token=data.get('access_token'), token_type=data.get('token_type'))
                else:
                    try:
                        err_json = resp.json()
                    except Exception:
                        err_json = {}
                    message = err_json.get('detail') or f'Falha no login (HTTP {resp.status_code}).'
                    return jsonify(success=False, message=message), resp.status_code
            except Exception:
                # Se houver erro de requests, cai para urllib
                pass

        form = urlparse.urlencode(form_payload).encode('utf-8')
        req = urlrequest.Request(api_url, data=form, headers={'Content-Type': 'application/x-www-form-urlencoded'})

        try:
            with urlrequest.urlopen(req, timeout=10) as resp:
                resp_body = resp.read().decode('utf-8')
                data = json.loads(resp_body)
                return jsonify(success=True, token=data.get('access_token'), token_type=data.get('token_type'))
        except HTTPError as e:
            err_body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
            try:
                err_json = json.loads(err_body) if err_body else {}
            except Exception:
                err_json = {}
            message = err_json.get('detail') or f'Falha no login (HTTP {e.code}).'
            return jsonify(success=False, message=message), e.code
        except URLError:
            return jsonify(success=False, message='Servidor de API indisponível.'), 503
        except Exception:
            return jsonify(success=False, message='Erro interno ao autenticar.'), 500
    except Exception:
        return jsonify(success=False, message='Erro ao processar requisição.'), 500

@app.route('/health')
def health():
    return jsonify(status='healthy'), 200

# Endpoint: Receita Total (proxy para a API FastAPI autenticada)
@app.route('/api/receita-total', methods=['GET'])
def api_receita_total():
    try:
        token = request.headers.get('X-Auth-Token')
        if not token:
            return jsonify(success=False, message='Token de autenticação ausente.'), 401

        api_url = 'http://127.0.0.1:8000/dashboard/kpis'

        # Tenta via requests primeiro
        if pyrequests is not None:
            try:
                resp = pyrequests.get(api_url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
                data = resp.json() if resp.content else {}
                if resp.status_code >= 200 and resp.status_code < 300 and isinstance(data, dict):
                    kpis = data.get('kpis') or []
                    receita = next((k for k in kpis if k.get('nome') == 'Receita Total'), None)
                    total = receita.get('valor') if receita else None
                    if total is None:
                        return jsonify(success=False, message='Receita não disponível.'), 200
                    return jsonify(success=True, total=float(total)), 200
                else:
                    msg = (data.get('detail') if isinstance(data, dict) else None) or f'Erro HTTP {resp.status_code}'
                    return jsonify(success=False, message=msg), resp.status_code
            except Exception:
                pass

        # Fallback via urllib
        req = urlrequest.Request(api_url, headers={'Authorization': f'Bearer {token}'})
        try:
            with urlrequest.urlopen(req, timeout=10) as resp:
                body = resp.read().decode('utf-8')
                data = json.loads(body) if body else {}
                kpis = data.get('kpis') or []
                receita = next((k for k in kpis if k.get('nome') == 'Receita Total'), None)
                total = receita.get('valor') if receita else None
                if total is None:
                    return jsonify(success=False, message='Receita não disponível.'), 200
                return jsonify(success=True, total=float(total)), 200
        except HTTPError as e:
            err_body = e.read().decode('utf-8') if hasattr(e, 'read') else ''
            try:
                err_json = json.loads(err_body) if err_body else {}
            except Exception:
                err_json = {}
            message = err_json.get('detail') or f'Falha ao consultar KPIs (HTTP {e.code}).'
            return jsonify(success=False, message=message), e.code
        except URLError:
            return jsonify(success=False, message='Servidor de API indisponível.'), 503
        except Exception:
            return jsonify(success=False, message='Erro interno ao consultar KPIs.'), 500
    except Exception:
        return jsonify(success=False, message='Erro ao processar requisição.'), 500

# Nota: Removida rota catch-all para evitar conflito com prefixo /api

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)