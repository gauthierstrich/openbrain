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
            
            # 1. Structure mémoire vide (aucune référence à un prénom spécifique)
            mem_dir = tmp_dir / "memory"
            for d in ["history", "journal", "facts"]:
                (mem_dir / d).mkdir(parents=True, exist_ok=True)
            (mem_dir / "history" / "conversation_history.json").write_text("[]", encoding="utf-8")
            (mem_dir / "history" / "history_summary.txt").write_text("", encoding="utf-8")
            (mem_dir / "facts" / "progress.md").write_text("# Suivi\n", encoding="utf-8")
            
            # 2. index.md générique
            now_iso = datetime.now().isoformat(timespec='seconds')
            index_content = f"""---
name: "{name.capitalize()}"
emoji: "{emoji}"
type: "{type_str}"
version: "1.0"
created: "{now_iso}"
---

# 🧠 Index de l'Expert : {name.capitalize()}

Ceci est le point d'entrée de ma mémoire. En tant qu'expert, j'ai pour instruction d'enrichir cette mémoire automatiquement (YOLO Mode) lors de mes échanges avec l'utilisateur, en créant des sous-fichiers dans `memory/facts/`.

- **Soul** : `soul.md` (Mon identité)
- **User** : `user.md` (Directives d'interaction de l'utilisateur)
- **Files** : *(Je remplirai cette liste de fichiers factuels dynamiquement via UPDATE_INDEX et SAVE_FACT)*
"""
            (tmp_dir / "index.md").write_text(index_content, encoding="utf-8")

            # 3. soul.md (DNA / Identité) avec consignes YOLO imposées
            soul_yolo_content = soul_content + f"""

## 🤫 GESTION DE LA MÉMOIRE (YOLO MODE)
Tu disposes d'un pouvoir d'écriture silencieux. Ne DEmande JAMAIS LA PERMISSION d'écrire.
Dès que l'utilisateur t'informe d'un fait important (loisir, projet, vie, code, etc.), tu DOIS utiliser cette commande pour le sauvegarder silencieusement en arrière-plan (sans inclure la balise dans le texte adressé à l'utilisateur):
- `[SYSTEM:SAVE_FACT file="nom_du_sujet.md" content="le contenu à sauvegarder..."]`
- `[SYSTEM:UPDATE_INDEX content="...réécriture de tout le fichier index.md pour inclure les nouveaux liens vers facts/nom_du_sujet.md..."]`
Exécute ces commandes pour construire ton cerveau.
"""
            (tmp_dir / "soul.md").write_text(soul_yolo_content, encoding="utf-8")

            # 4. user.md (Préférences d'interaction)
            (tmp_dir / "user.md").write_text(user_content, encoding="utf-8")
            
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
