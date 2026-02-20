"""
Script para inicializar banco de dados
"""

import sys
import os
from pathlib import Path

# Adiciona diretórios ao path
ROOT_DIR = Path(__file__).resolve().parent
WEB_MODULE = ROOT_DIR / "web_module"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(WEB_MODULE))

# Importa usando importlib
import importlib.util

# Carrega módulo database
spec = importlib.util.spec_from_file_location("database", WEB_MODULE / "database" / "__init__.py")
database_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database_module)

if __name__ == "__main__":
    print("Inicializando banco de dados...")
    try:
        database_module.init_db(criar_dados_exemplo=True)
        print("✓ Banco de dados inicializado com sucesso!")
        print("✓ Usuário admin criado (username: admin, senha: admin123)")
    except Exception as e:
        print(f"✗ Erro ao inicializar banco: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
