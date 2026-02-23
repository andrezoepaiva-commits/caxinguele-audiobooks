#!/usr/bin/env python3
"""
Setup automático do Projeto Caxinguele v2
Verifica e configura dependências, caminhos, credenciais
"""

import sys
import subprocess
import json
from pathlib import Path

def check_python():
    """Verifica versão Python"""
    if sys.version_info < (3, 9):
        print(f"ERRO: Python 3.9+ requerido (tem {sys.version_info.major}.{sys.version_info.minor})")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True

def check_dependencies():
    """Verifica pacotes instalados"""
    required = ['edge_tts', 'fitz', 'docx', 'google', 'tkinter']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg if pkg != 'fitz' else 'fitz')
            print(f"  ✓ {pkg}")
        except ImportError:
            missing.append(pkg)
            print(f"  ✗ {pkg}")
    
    if missing:
        print(f"\nInstalando {len(missing)} pacote(s)...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        return check_dependencies()
    return True

def check_credentials():
    """Verifica configuração do Google Drive"""
    cred_file = Path('credentials.json')
    token_file = Path('token.json')
    
    if cred_file.exists():
        print("✓ credentials.json encontrado")
    else:
        print("✗ credentials.json faltando")
        print("  → Baixe de Google Cloud Console")
        return False
    
    if token_file.exists():
        print("✓ token.json encontrado (autenticado)")
        return True
    else:
        print("⏳ token.json faltando — será criado na primeira execução")
        return True

def check_data_files():
    """Verifica arquivos de dados"""
    files = [
        'menus_config.json',
        'compromissos.json',
        'favoritos.json',
        'listas_mentais.json',
        'reunioes.json'
    ]
    
    for f in files:
        path = Path(f)
        if path.exists():
            size = path.stat().st_size
            print(f"✓ {f} ({size} bytes)")
        else:
            print(f"✗ {f} faltando")
    return all(Path(f).exists() for f in files)

def main():
    print("="*60)
    print("SETUP — Projeto Caxinguele v2")
    print("="*60 + "\n")
    
    checks = [
        ("Python", check_python),
        ("Dependências", check_dependencies),
        ("Credenciais Google Drive", check_credentials),
        ("Arquivos de dados", check_data_files),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n[{len(results)+1}/{len(checks)}] {name}...")
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"  ERRO: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("RESUMO:")
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    all_ok = all(r for _, r in results)
    if all_ok:
        print("\n✓ Sistema pronto! Execute: python audiobook_gui.py")
    else:
        print("\n✗ Alguns problemas detectados. Veja acima.")
        sys.exit(1)

if __name__ == "__main__":
    main()
