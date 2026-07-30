"""
Gene-In Dashboard Server Launcher Module
Inicialização do servidor HTTP multithreaded e tratamento de argumentos CLI.
"""

import argparse
import logging
import os
import shutil
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "lib"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "evidence"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dashboard.config import (
    CONFIG_ENV_PRIMARY, CONFIG_ENV_EXAMPLE, get_config_env_path,
    parse_env_file, is_loopback_host,
)
from dashboard.handler import DashboardHandler, logger


def _ensure_config_env():
    """Bootstrap config/picornavirus.env from the bundled example if it doesn't exist yet."""
    if not CONFIG_ENV_PRIMARY.exists():
        if CONFIG_ENV_EXAMPLE.exists():
            CONFIG_ENV_PRIMARY.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(CONFIG_ENV_EXAMPLE, CONFIG_ENV_PRIMARY)
            logger.info(
                "config/picornavirus.env criado a partir do exemplo: %s", CONFIG_ENV_EXAMPLE.name
            )
        else:
            logger.warning(
                "config/picornavirus.env não encontrado e nenhum .example disponível; "
                "usando config.env como fallback."
            )


def run_server(args_list=None):
    config_defaults = parse_env_file(get_config_env_path())
    default_host = os.environ.get("BIND_HOST") or config_defaults.get("BIND_HOST") or "127.0.0.1"
    try:
        default_port = int(os.environ.get("PORT") or config_defaults.get("PORT") or "8000")
    except ValueError:
        default_port = 8000

    parser = argparse.ArgumentParser(description="Painel local do Gene-In")
    parser.add_argument(
        "--host", default=default_host,
        help="Endereço de escuta. Padrão vem de BIND_HOST no config. "
             "Somente localhost e endereços loopback são aceitos."
    )
    parser.add_argument("--port", default=default_port, type=int)
    args = parser.parse_args(args_list)

    if not is_loopback_host(args.host):
        print("[ERRO] O dashboard aceita somente enderecos loopback (127.0.0.1/localhost).")
        print("       A exposicao na rede exige uma modalidade autenticada futura.")
        raise SystemExit(2)
    if not 1 <= args.port <= 65535:
        print("[ERRO] A porta deve estar entre 1 e 65535.")
        raise SystemExit(2)

    _ensure_config_env()

    ThreadingHTTPServer.allow_reuse_address = True
    try:
        server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    except OSError as exc:
        if getattr(exc, "errno", None) in {98, 10048}:
            logger.error("Porta %s indisponivel em %s: %s", args.port, args.host, exc)
            print(f"[ERRO] A porta {args.port} ja esta em uso.")
            print("Feche o dashboard aberto anteriormente ou inicie em outra porta:")
            print(f"  python3 scripts/ux_dashboard.py --host {args.host} --port {args.port + 1}")
            raise SystemExit(1) from exc
        raise

    print("Painel ativo em:")
    print(f"  http://localhost:{args.port}")
    if args.host not in ("127.0.0.1", "localhost"):
        print(f"  http://{args.host}:{args.port}  ← exposto na rede")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando painel...")
