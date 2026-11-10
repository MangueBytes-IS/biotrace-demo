"""
Exclui uma conta e todos os seus dados (análises, Excel, sessões).

Uso (no servidor, dentro do container ou com o mesmo DATA_FILE/ANALYSES_DIR da API):
    python delete_user.py email@exemplo.com

Não altera o estado da API; a API lê o arquivo na próxima requisição.
Os backups (ver deploy/backup.sh) também precisam ser apagados ou expirados.
"""
import json
import os
import sys

DATA_FILE = os.getenv('DATA_FILE', 'data.json')


def delete_user(email):
    email = email.strip().lower()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    users = data.get('users', {})
    analyses = data.get('analyses', [])
    owned = [a for a in analyses if a.get('email') == email]

    if email not in users and not owned:
        print(f'Conta não encontrada: {email}')
        return 1

    removed_files = 0
    for a in owned:
        result_file = a.get('result_file')
        if result_file and os.path.exists(result_file):
            os.remove(result_file)
            removed_files += 1

    data['analyses'] = [a for a in analyses if a.get('email') != email]
    users.pop(email, None)
    sessions = data.get('sessions', {})
    for token in [t for t, e in sessions.items() if e == email]:
        del sessions[token]

    tmp_file = f'{DATA_FILE}.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_file, DATA_FILE)

    print(f'Conta excluída: {email} | análises removidas: {len(owned)} | arquivos apagados: {removed_files}')
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Uso: python delete_user.py email@exemplo.com')
        sys.exit(2)
    sys.exit(delete_user(sys.argv[1]))
