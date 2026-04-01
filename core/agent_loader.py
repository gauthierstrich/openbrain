import os
import shutil
import re
from pathlib import Path
from dataclasses import dataclass
from core import config

@dataclass
class AgentConfig:
    id: str
    name: str
    emoji: str
    path: Path
    type: str
    description: str

class AgentLoader:
    """
    Scanner Plug & Play V1.2 (Modular Agent Brain).
    Scanne index.md et assure la migration automatique.
    """
    
    def __init__(self):
        self.agents_dir = config.AGENTS_DIR

    def cleanup_orphans(self):
        if not self.agents_dir.exists():
            return
        for path in self.agents_dir.iterdir():
            if path.is_dir() and path.name.startswith("_tmp_"):
                try:
                    shutil.rmtree(path)
                except Exception:
                    pass

    def scan(self) -> dict[str, AgentConfig]:
        """Scanne le répertoire et retourne les agents valides (V1.2)."""
        self.cleanup_orphans()
        agents = {}
        if not self.agents_dir.exists():
            return agents
            
        for path in self.agents_dir.iterdir():
            if not path.is_dir() or path.name.startswith("_"):
                continue
                
            # 1. Auto-migration V1.1 -> V1.2 (Soul -> Index pour Frontmatter)
            soul_path = path / "soul.md"
            index_path = path / "index.md"
            
            # Si index.md n'existe pas, on le crée à partir de soul.md si possible
            if not index_path.exists() and soul_path.exists():
                content = soul_path.read_text(encoding="utf-8")
                # On extrait le frontmatter de soul.md pour le mettre dans index.md
                match = re.search(r'---\s*(.*?)\s*---', content, re.DOTALL)
                if match:
                    frontmatter = match.group(0)
                    index_path.write_text(frontmatter + "\n\n# Index de l'Agent\nEntrée principale.", encoding="utf-8")
                    # On nettoie soul.md du frontmatter
                    clean_soul = re.sub(r'---\s*.*?\s*---', '', content, flags=re.DOTALL).strip()
                    soul_path.write_text(clean_soul, encoding="utf-8")

            if not index_path.exists():
                continue
                
            # 2. Parse index.md (Source de vérité pour l'UI)
            content = index_path.read_text(encoding="utf-8")
            name = self._extract_yaml(content, "name", path.name)
            emoji = self._extract_yaml(content, "emoji", "🤖")
            type_str = self._extract_yaml(content, "type", "specialist")
            desc = self._extract_yaml(content, "description", "")
            
            # 3. Auto-réparation
            self.auto_repair_v1_2(path)
            
            agents[path.name] = AgentConfig(
                id=path.name,
                name=name,
                emoji=emoji,
                path=path,
                type=type_str,
                description=desc
            )
        return agents

    def auto_repair_v1_2(self, agent_path: Path):
        """Assure la présence des 4 piliers (Index, Soul, User, Memory)."""
        # Soul pilier (DNA)
        soul_file = agent_path / "soul.md"
        if not soul_file.exists():
            soul_file.write_text("# DNA\nInstructions par défaut.", encoding="utf-8")

        # User pilier
        user_file = agent_path / "user.md"
        if not user_file.exists():
            user_file.write_text("# Préférences Utilisateur\nPar défaut, utilise le profil global.", encoding="utf-8")
            
        # Memory pilier
        mem_dir = agent_path / "memory"
        for d in ["history", "journal", "facts"]:
            (mem_dir / d).mkdir(parents=True, exist_ok=True)
            
        hist_file = mem_dir / "history" / "conversation_history.json"
        if not hist_file.exists():
            hist_file.write_text("[]", encoding="utf-8")
            
        sum_file = mem_dir / "history" / "history_summary.txt"
        if not sum_file.exists():
            sum_file.write_text("", encoding="utf-8")

    def _extract_yaml(self, content: str, key: str, default: str) -> str:
        match = re.search(fr'^{key}:\s*"(.*?)"', content, re.MULTILINE)
        if match: return match.group(1)
        match = re.search(fr'^{key}:\s*(.*?)$', content, re.MULTILINE)
        if match: return match.group(1).strip()
        return default
