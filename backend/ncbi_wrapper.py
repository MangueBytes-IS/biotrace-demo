"""
Wrapper para executar ncbi_collector.py como função reutilizável
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback

# Linha do tqdm do loop principal, ex: "Espécies:  24%|██▍  | 12/49 [00:31<01:20, ...]"
SPECIES_PROGRESS_RE = re.compile(r'Esp\S*cies:\s*\d+%\|.*?\|\s*(\d+)/(\d+)')

# Limite da versão demo: ~3 min por espécie => 20 espécies ≈ 60 min.
# 63 min dá 3 min de margem para as 20 passarem, mas não chega a uma 21ª espécie.
DEMO_SPECIES_LIMIT = 20
MINUTES_PER_SPECIES = 3
COLLECTION_TIMEOUT = (DEMO_SPECIES_LIMIT * MINUTES_PER_SPECIES + 3) * 60

UNEXPECTED_ERROR_MESSAGE = (
    'A coleta foi interrompida por um erro inesperado. '
    'Confira os nomes das espécies no CSV e tente de novo. '
    'Se o problema continuar, entre em contato com o suporte.'
)

DEMO_LIMIT_MESSAGE = (
    f'Você excedeu o limite da versão demo. '
    f'Nesta versão é possível analisar até {DEMO_SPECIES_LIMIT} espécies por análise.'
)


def _safe_name(name):
    name = re.sub(r'[^A-Za-z0-9._-]+', '-', name or '').strip('-.')
    return name or 'species'


def run_collection(species_list, output_dir=None, email=None, dataset_name=None, on_progress=None):
    """
    Executa coleta NCBI para lista de espécies

    Args:
        species_list: lista de nomes científicos (ex: ["Panthera leo", "Panthera tigris"])
        output_dir: diretório para salvar Excel (default: ./analyses)
        email: e-mail repassado ao NCBI (Entrez.email) via NCBI_EMAIL
        dataset_name: nome usado no arquivo de saída (default: "species")
        on_progress: callback(percent: int, message: str) chamado durante a coleta

    Returns:
        tuple: (success: bool, result_path: str or error_msg: str)
    """
    temp_dir = tempfile.mkdtemp()
    try:
        if output_dir is None:
            output_dir = 'analyses'
        os.makedirs(output_dir, exist_ok=True)

        csv_path = os.path.join(temp_dir, f'{_safe_name(dataset_name)}.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            for species in species_list:
                f.write(species.strip() + '\n')

        # O script fica no mesmo diretório (Docker) ou um nível acima (local)
        app_dir = os.path.dirname(os.path.abspath(__file__))
        collector_path = os.path.join(app_dir, 'ncbi_collector.py')
        if not os.path.exists(collector_path):
            collector_path = os.path.join(os.path.dirname(app_dir), 'ncbi_collector.py')

        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        if email:
            env['NCBI_EMAIL'] = email

        proc = subprocess.Popen(
            [sys.executable, collector_path, csv_path],
            cwd=app_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Timer independente da saída do processo: o read abaixo pode ficar bloqueado
        timed_out = threading.Event()

        def _kill_on_timeout():
            timed_out.set()
            proc.kill()

        watchdog = threading.Timer(COLLECTION_TIMEOUT, _kill_on_timeout)
        watchdog.daemon = True
        watchdog.start()

        log_tail = []
        buffer = ''
        last_percent = -1

        while True:
            chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, 'read1') else proc.stdout.read(4096)
            if not chunk:
                break
            buffer += chunk.decode('utf-8', errors='replace')
            # tqdm usa \r para redesenhar a mesma linha
            parts = re.split(r'[\r\n]', buffer)
            buffer = parts.pop()
            for line in parts:
                line = line.strip()
                if not line:
                    continue
                log_tail = (log_tail + [line])[-40:]
                match = SPECIES_PROGRESS_RE.search(line)
                if match and on_progress:
                    done, total = int(match.group(1)), int(match.group(2))
                    # O loop de espécies representa até 85%; o resto é reprocessamento e exportação
                    percent = int(5 + 80 * done / max(total, 1))
                    if percent != last_percent:
                        last_percent = percent
                        on_progress(percent, f'Consultando NCBI ({done}/{total} espécies)')
                elif on_progress and 'Reprocessando' in line:
                    on_progress(88, 'Reprocessando falhas')
                elif on_progress and 'AMOSTRA DATAS' in line:
                    on_progress(92, 'Gerando relatório Excel')

        proc.wait()
        watchdog.cancel()
        if timed_out.is_set():
            return False, DEMO_LIMIT_MESSAGE

        output_text = '\n'.join(log_tail + ([buffer.strip()] if buffer.strip() else []))

        if proc.returncode != 0:
            # Log técnico fica no servidor; o usuário vê uma mensagem tratada
            print(f'[coleta] processo falhou (código {proc.returncode}):\n{output_text}', file=sys.stderr)
            return False, UNEXPECTED_ERROR_MESSAGE

        # O coletor grava em ./output relativo ao cwd (app_dir)
        match = re.search(r'Arquivo gerado:\s*(\S+\.xlsx)', output_text)
        if match:
            source_file = os.path.join(app_dir, match.group(1))
        else:
            output_path = os.path.join(app_dir, 'output')
            files = sorted(
                [f for f in os.listdir(output_path) if f.endswith('.xlsx')] if os.path.isdir(output_path) else [],
                key=lambda f: os.path.getctime(os.path.join(output_path, f)),
                reverse=True,
            )
            if not files:
                return False, "Nenhum arquivo Excel gerado"
            source_file = os.path.join(output_path, files[0])

        if not os.path.exists(source_file):
            return False, "Arquivo Excel gerado não foi encontrado"

        dest_file = os.path.join(output_dir, os.path.basename(source_file))
        shutil.copyfile(source_file, dest_file)
        return True, dest_file

    except Exception as e:
        return False, f"Erro na coleta: {str(e)}\n{traceback.format_exc()}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
