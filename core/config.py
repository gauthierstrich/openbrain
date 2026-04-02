import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Repertoires fondamentaux
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Paramètres du Moteur
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.0-flash-preview")
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-3.1-pro-preview")

# Configuration du Second Brain
# Fallback local par défaut si .env non configuré correctement
default_storage = str(ROOT_DIR / "template") 
raw_storage = os.getenv("BRAIN_STORAGE_PATH", default_storage)
STORAGE_ROOT = Path(os.path.expanduser(raw_storage))

# Chemins de structure de base
IDENTITY_DIR = STORAGE_ROOT / "identity"
AGENTS_DIR = STORAGE_ROOT / "agents"

# Chargement dynamique des préférences de l'utilisateur
def get_user_name() -> str:
    user_file = IDENTITY_DIR / "user.md"
    if not user_file.exists():
        return "Utilisateur"
    
    content = user_file.read_text(encoding="utf-8")
    # Chercher "# Profil de {Nom}"
    match = re.search(r'# Profil de (.+)', content)
    if match:
        return match.group(1).strip()
    return "Utilisateur"

USER_NAME = get_user_name()
USER_LANGUAGE = os.getenv("USER_LANGUAGE", "fr")
