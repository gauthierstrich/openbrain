import os
import re
import shutil
import json
from datetime import datetime
from pathlib import Path
from core import config

class AgentCreationError(Exception):
    pass

class AgentCreator:
    """
    Système de Création d'Agents V1.4 (Universal & Agnostic Setup)
    Structure : index.md, soul.md, user.md, memory/
    """

    NAME_PATTERN = r'^[a-z][a-z0-9_-]{1,30}$'
    RESERVED_NAMES = ['_example', '_tmp', 'shared', 'core', 'template']
    
    def __init__(self):
        self.agents_dir = config.AGENTS_DIR

    def validate_name(self, name: str) -> tuple[bool, str]:
        if not re.match(self.NAME_PATTERN, name):
            return False, "Le nom doit comporter au plus 30 caractères (minuscules, chiffres, tirets)."
        if name in self.RESERVED_NAMES or name.startswith("_"):
            return False, f"Le nom '{name}' est réservé ou invalide."
        return True, "Nom valide."

    def create_agent(self, name: str, soul_content: str, user_content: str, emoji: str = "🤖", type_str: str = "specialist") -> Path:
        """Crée ou met à jour un agent. Ardoise vierge pour que ce soit compatible avec les amis de Gauthier."""
        is_valid, err_msg = self.validate_name(name)
        if not is_valid: raise AgentCreationError(err_msg)

        target_dir = self.agents_dir / name
        tmp_dir = self.agents_dir / f"_tmp_{name}"
        
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
            
            # 1. Structure Obsidian Premium (V2.5)
            dirs = {
                "journal": tmp_dir / "📓 01 - Journal",
                "memory": tmp_dir / "🧠 02 - Mémoire",
                "config": tmp_dir / "⚙️ 03 - Configuration",
                "archives": tmp_dir / "04 - Archives" / "history"
            }
            for d in dirs.values(): d.mkdir(parents=True, exist_ok=True)
            
            (dirs["archives"] / "conversation_history.json").write_text("[]", encoding="utf-8")
            (dirs["archives"] / "history_summary.txt").write_text("", encoding="utf-8")
            (dirs["memory"] / "progress.md").write_text("# 📈 Suivi de Progression\n", encoding="utf-8")
            
            # 2. Configuration (Soul, Index, User)
            now_iso = datetime.now().isoformat(timespec='seconds')
            index_content = f"""---
type: dashboard
name: "{name.capitalize()}"
emoji: "{emoji}"
created: "{now_iso}"
---

# 🧠 Dashboard Expert : {name.capitalize()} {emoji}

Ceci est mon centre de contrôle. En tant qu'expert, j'enrichis ma mémoire automatiquement dans le dossier `🧠 02 - Mémoire/`.

- **Identité** : `soul.md`
- **Préférences** : `user.md`
- **Journal** : `[[📓 01 - Journal/]]`
- **Base de Connaissances** : `[[🧠 02 - Mémoire/]]`
"""
            (dirs["config"] / "index.md").write_text(index_content, encoding="utf-8")

            # 3. soul.md (DNA / Identité) 
            soul_yolo_content = soul_content + f"""

## 🤫 GESTION DE LA MÉMOIRE (YOLO MODE V2.5)
Tu es un agent Obsidian-Ready. Toute information importante sur {config.USER_NAME} ou tes progrès doit être sauvegardée :
- `[SYSTEM:SAVE_FACT file="02 - Mémoire/nom_sujet.md" content="..."]`
- `[SYSTEM:UPDATE_INDEX content="..."]`
Utilise des [[Wikilinks]] pour connecter tes notes.
"""
            (dirs["config"] / "soul.md").write_text(soul_yolo_content, encoding="utf-8")
            (dirs["config"] / "user.md").write_text(user_content, encoding="utf-8")
            
            # 5. Atomic swap
            if target_dir.exists(): shutil.rmtree(target_dir)
            os.rename(tmp_dir, target_dir)
            return target_dir
            
        except Exception as e:
            if tmp_dir.exists(): shutil.rmtree(tmp_dir)
            raise AgentCreationError(f"Erreur création V1.4 : {str(e)}")

    def delete_agent(self, name: str) -> bool:
        if name == 'personal': raise AgentCreationError("Impossible de supprimer l'agent principal.")
        target_dir = self.agents_dir / name
        if not target_dir.exists(): return False
        trash_dir = self.agents_dir / f"_trash_{name}_{int(datetime.now().timestamp())}"
        os.rename(target_dir, trash_dir)
        return True
