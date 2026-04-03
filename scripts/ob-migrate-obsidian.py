#!/usr/bin/env python3
import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Nouveaux dossiers (Standard Obsidian Premium)
FOLDERS = {
    "journal": "📓 01 - Journal",
    "facts": "🧠 02 - Mémoire",
    "config": "⚙️ 03 - Configuration"
}

def migrate_agent(agent_path: Path):
    print(f"\n📁 Migration de l'agent : {agent_path.name}")
    
    # 1. Création des nouveaux dossiers
    new_paths = {k: agent_path / v for k, v in FOLDERS.items()}
    for p in new_paths.values():
        p.mkdir(parents=True, exist_ok=True)
        
    old_mem = agent_path / "memory"
    
    # 2. Migration du Journal
    old_journal = old_mem / "journal"
    if old_journal.exists():
        for f in old_journal.iterdir():
            if f.is_file():
                shutil.move(str(f), str(new_paths["journal"] / f.name))
        print(f"✅ Journal migré vers {FOLDERS['journal']}")
        
    # 3. Migration des Faits
    old_facts = old_mem / "facts"
    if old_facts.exists():
        for f in old_facts.iterdir():
            if f.is_file():
                shutil.move(str(f), str(new_paths["facts"] / f.name))
        print(f"✅ Faits migrés vers {FOLDERS['facts']}")
        
    # 4. Migration de la Configuration (Soul, Index, User)
    config_files = ["index.md", "soul.md", "user.md"]
    for cf in config_files:
        old_cf = agent_path / cf
        if old_cf.exists():
            shutil.move(str(old_cf), str(new_paths["config"] / cf))
    print(f"✅ Configuration migrée vers {FOLDERS['config']}")
    
    # 5. Nettoyage de l'ancien dossier memory (en gardant la DB)
    if old_mem.exists():
        # On garde seulement la DB pour éviter de tout ré-indexer
        db_path = old_mem / "memory_index.db"
        if db_path.exists():
            # On la déplace temporairement
            shutil.move(str(db_path), str(agent_path / "memory_index.db"))
            
        # On supprime le reste
        shutil.rmtree(old_mem, ignore_errors=True)
        
        # On remet la DB à la racine de l'agent (car brain.py pointera là)
        # Mais en V2.5, on va la placer dans Configuration pour la cacher ?
        # Non, on va la laisser à la racine de l'agent pour la simplicité technique
        if (agent_path / "memory_index.db").exists():
            (agent_path / "memory").mkdir()
            shutil.move(str(agent_path / "memory_index.db"), str(agent_path / "memory" / "memory_index.db"))

def main():
    raw_storage = os.getenv("BRAIN_STORAGE_PATH")
    if not raw_storage:
        print("❌ Erreur : BRAIN_STORAGE_PATH non configuré.")
        return
        
    storage_root = Path(os.path.expanduser(raw_storage))
    agents_dir = storage_root / "agents"
    
    if not agents_dir.exists():
        print(f"❌ Erreur : Dossier agents introuvable dans {agents_dir}")
        return
        
    for d in agents_dir.iterdir():
        if d.is_dir() and not d.name.startswith(("_", ".")):
            migrate_agent(d)
            
    print("\n✨ Migration du Second Cerveau (V2.5) terminée avec succès !")
    print("👉 Tu peux maintenant ouvrir ton dossier 'agents/' dans Obsidian.")

if __name__ == "__main__":
    main()
