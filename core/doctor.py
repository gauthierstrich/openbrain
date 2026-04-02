import sys
import os
import subprocess
from pathlib import Path

class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

def print_check(name, success, info=""):
    status = f"{C.GREEN}✓{C.RESET}" if success else f"{C.RED}✗{C.RESET}"
    print(f"[{status}] {name} {info}")

def run_doctor():
    print("🩺 OpenBrain Core - Diagnostic System\n")
    all_ok = True

    py_ok = sys.version_info >= (3, 10)
    print_check("Python 3.10+", py_ok, f"({sys.version.split()[0]})")
    if not py_ok: all_ok = False

    try:
        res = subprocess.run(["gemini", "--version"], capture_output=True, text=True)
        gem_ok = res.returncode == 0
        print_check("Gemini CLI", gem_ok, "Installé" if gem_ok else "Non trouvé")
        if not gem_ok: all_ok = False
    except FileNotFoundError:
        print_check("Gemini CLI", False, "Non trouvé dans le PATH")
        all_ok = False

    # Check OAuth (V2.1 Requirement)
    oauth_path = Path.home() / ".gemini" / "oauth_creds.json"
    auth_ok = oauth_path.exists()
    print_check("Authentification (OAuth)", auth_ok, "OK" if auth_ok else "Manquante")
    if not auth_ok: 
        all_ok = False
        print(f"   {C.YELLOW}👉 Action requise : Tapez 'gemini login' dans votre terminal.{C.RESET}")

    try:
        res = subprocess.run(["git", "--version"], capture_output=True, text=True)
        git_ok = res.returncode == 0
        print_check("Git", git_ok)
    except FileNotFoundError:
        print_check("Git", False, "Recommandé pour versionner la mémoire")

    print("\nRésultat : ", end="")
    if all_ok:
        print(f"{C.GREEN}Système Prêt !{C.RESET}")
        return 0
    else:
        print(f"{C.RED}Des erreurs ont été détectées. Veuillez installer les pré-requis.{C.RESET}")
        if not gem_ok:
            print("Installation Gemini CLI: npm install -g @google/gemini-cli")
        return 1

if __name__ == "__main__":
    sys.exit(run_doctor())
