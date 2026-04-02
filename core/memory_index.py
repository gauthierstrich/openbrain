#!/usr/bin/env python3
"""
OpenBrain Core — Module de Recherche Hybride dans la Mémoire V2.0
Inspiré du pattern memory-search d'OpenClaw.

Deux couches de recherche :
  1. SQLite FTS5 (mots-clés + BM25) — zéro dépendance
  2. Embeddings Gemini API (cosine similarity) — optionnel, dégradation gracieuse

Stratégie d'authentification pour les embeddings (par ordre de priorité) :
  a. Clé API (GOOGLE_API_KEY ou GEMINI_API_KEY) via google-genai SDK
  b. Token OAuth du Gemini CLI (~/.gemini/oauth_creds.json) via REST API directe
  c. Aucun embedding → FTS5 uniquement (le système fonctionne quand même)
"""
import sqlite3
import json
import math
import hashlib
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# ─── Constantes ──────────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 256  # Dimension réduite pour la rapidité
FTS_WEIGHT = 0.35
VECTOR_WEIGHT = 0.65
DEFAULT_TOP_K = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBED_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent"

# ─── Stratégie OAuth / CLI ───────────────────────────────────────────

def _get_oauth_token() -> Optional[str]:
    """Tente de récupérer le token OAuth depuis le fichier Gemini CLI."""
    token_path = Path.home() / ".gemini" / "oauth_creds.json"
    if token_path.exists():
        try:
            creds = json.loads(token_path.read_text(encoding="utf-8"))
            return creds.get("access_token")
        except Exception:
            pass
    return None

def _get_active_project() -> Optional[str]:
    """Tente d'associer le dossier actuel à un nom de projet Gemini CLI."""
    projects_path = Path.home() / ".gemini" / "projects.json"
    if not projects_path.exists():
        return None
    try:
        data = json.loads(projects_path.read_text(encoding="utf-8"))
        projects = data.get("projects", {})
        current_dir = str(Path.cwd().resolve())
        
        # On trie par longueur de chemin décroissante pour trouver le match le plus précis
        sorted_paths = sorted(projects.keys(), key=len, reverse=True)
        for path_str in sorted_paths:
            if current_dir.startswith(str(Path(path_str).resolve())):
                return projects[path_str]
    except Exception:
        pass
    return None

_genai_available = False
_genai_client = None
try:
    from google import genai
    from google.genai import types as genai_types
    _genai_available = True
except ImportError:
    pass


def _get_ssl_context():
    """Retourne un contexte SSL compatible macOS."""
    try:
        import certifi
        import ssl
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return None


def _embed_via_rest(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[list[float]]:
    """Appelle l'API Gemini Embeddings via REST (Pattern OpenClaw Auth)."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    oauth_token = _get_oauth_token()
    project_id = _get_active_project()
    
    if not api_key and not oauth_token:
        return None

    # On utilise le format JSON pour l'Auth si on a un token
    payload = json.dumps({
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text[:2000]}]},
        "outputDimensionality": EMBEDDING_DIM,
        "taskType": task_type,
    }).encode("utf-8")

    # Si on a une clé API, on l'utilise en priorité
    url = f"{EMBED_API_URL}?key={api_key}" if api_key else EMBED_API_URL
    headers = {"Content-Type": "application/json"}
    
    # Sinon, on utilise le token OAuth comme Bearer (Pattern OpenClaw infra/gemini-auth.ts)
    if not api_key and oauth_token:
        headers["Authorization"] = f"Bearer {oauth_token}"

    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        ctx = _get_ssl_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read())
            # Gestion du format de réponse embedding
            if "embedding" in data:
                return data["embedding"]["values"]
            return None
    except Exception:
        return None


def _init_genai_client():
    """Obsolète : on préfère l'authentification REST avec OAuth CLI."""
    return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcule la similarité cosinus entre deux vecteurs."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Découpe un texte en morceaux pour l'indexation (pattern OpenClaw)."""
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start += chunk_size - overlap
    return chunks


class MemoryIndex:
    """
    Index hybride pour la mémoire d'un agent.
    Stocke un index FTS5 (mots-clés) et des embeddings vectoriels (sémantique)
    dans un fichier SQLite local par agent.
    """

    def __init__(self, agent_path: Path):
        """
        Args:
            agent_path: Chemin racine de l'agent (ex: agents/personal/)
        """
        self.agent_path = agent_path
        self.facts_dir = agent_path / "memory" / "facts"
        self.db_path = agent_path / "memory" / "memory_index.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _ensure_schema(self):
        """Crée les tables nécessaires si elles n'existent pas."""
        conn = self._get_conn()
        
        # Vérification si chunk_index existe, sinon on redémarre l'index (Migration V2.1)
        try:
            conn.execute("SELECT chunk_index FROM documents LIMIT 1")
        except sqlite3.OperationalError:
            conn.executescript("""
                DROP TABLE IF EXISTS documents;
                DROP TABLE IF EXISTS documents_fts;
                DROP TRIGGER IF EXISTS documents_ai;
                DROP TRIGGER IF EXISTS documents_ad;
                DROP TRIGGER IF EXISTS documents_au;
            """)

        conn.executescript("""
            -- Table principale des documents indexés (avec chunking)
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding BLOB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(filename, chunk_index)
            );

            -- Index FTS5 pour la recherche full-text
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts
            USING fts5(filename, content, content=documents, content_rowid=id);

            -- Trigger pour maintenir FTS5 synchronisé
            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, filename, content)
                VALUES (new.id, new.filename, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, filename, content)
                VALUES('delete', old.id, old.filename, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, filename, content)
                VALUES('delete', old.id, old.filename, old.content);
                INSERT INTO documents_fts(rowid, filename, content)
                VALUES (new.id, new.filename, new.content);
            END;
        """)
        conn.commit()

    # ─── Indexation ──────────────────────────────────────────────────

    def _index_directory(self, directory: Path, rel_prefix: str) -> dict:
        """
        Scanne un dossier et (ré)indexe les fichiers modifiés par morceaux (chunks).
        SHA-256 est utilisé pour la comparaison.
        """
        if not directory.exists():
            return {"indexed": 0, "skipped": 0, "removed": 0}

        conn = self._get_conn()
        report = {"indexed": 0, "skipped": 0, "removed": 0}

        # Fichiers actuellement sur disque
        disk_files = {}
        for f in directory.iterdir():
            if f.is_file() and f.suffix == ".md":
                filename = f"{rel_prefix}/{f.name}"
                content = f.read_text(encoding="utf-8").strip()
                if not content:
                    continue
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                disk_files[filename] = (content, content_hash)

        # Fichiers dans l'index (on vérifie le hash sur le chunk_index=0)
        indexed_hashes = {
            row[0]: row[1]
            for row in conn.execute("SELECT filename, content_hash FROM documents WHERE chunk_index=0 AND filename LIKE ?", (f"{rel_prefix}/%",))
        }

        # Pour les suppressions
        all_indexed_files = {
            row[0]
            for row in conn.execute("SELECT DISTINCT filename FROM documents WHERE filename LIKE ?", (f"{rel_prefix}/%",))
        }

        # Supprimer les fichiers disparus du disque
        for filename in all_indexed_files:
            if filename not in disk_files:
                conn.execute("DELETE FROM documents WHERE filename = ?", (filename,))
                report["removed"] += 1

        # Indexer les fichiers nouveaux ou modifiés
        for filename, (content, content_hash) in disk_files.items():
            if filename in indexed_hashes and indexed_hashes[filename] == content_hash:
                report["skipped"] += 1
                continue

            # Nouveaux ou modifiés : purger anciens chunks d'abord
            conn.execute("DELETE FROM documents WHERE filename = ?", (filename,))

            chunks = chunk_text(content)
            for i, chunk in enumerate(chunks):
                embedding_blob = None
                embedding = self._embed_text(chunk)
                if embedding:
                    embedding_blob = json.dumps(embedding).encode("utf-8")

                conn.execute(
                    "INSERT INTO documents (filename, chunk_index, content, content_hash, embedding) VALUES (?, ?, ?, ?, ?)",
                    (filename, i, chunk, content_hash, embedding_blob),
                )
            report["indexed"] += 1

        conn.commit()
        return report

    def index_facts(self) -> dict:
        return self._index_directory(self.facts_dir, "facts")

    def index_journals(self) -> dict:
        return self._index_directory(self.agent_path / "memory" / "journal", "journal")

    # ─── Recherche hybride ───────────────────────────────────────────

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        """
        Recherche hybride : FTS5 (BM25) + Embeddings (Cosine Similarity).
        Retourne les top_k morceaux (chunks) les plus pertinents.

        Returns:
            Liste de dicts : [{filename, chunk_index, content, score}, ...]
        """
        conn = self._get_conn()

        # S'assurer que l'index est à jour pour facts et journals
        self.index_facts()
        self.index_journals()

        # Tous les documents (chunks)
        all_docs = list(conn.execute(
            "SELECT id, filename, chunk_index, content, embedding FROM documents"
        ))
        if not all_docs:
            return []

        scores = {}  # filename -> {fts_score, vec_score, content}

        # ─── Couche 1 : FTS5 / BM25 ─────────────────────────────────
        fts_results = {}
        try:
            # BM25 retourne des scores négatifs (plus négatif = plus pertinent)
            rows = conn.execute(
                "SELECT rowid, bm25(documents_fts) as rank FROM documents_fts WHERE documents_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, top_k * 2),
            ).fetchall()
            if rows:
                # Normaliser les scores BM25 entre 0 et 1
                min_rank = min(r[1] for r in rows)
                max_rank = max(r[1] for r in rows)
                range_rank = max_rank - min_rank if max_rank != min_rank else 1.0
                for rowid, rank in rows:
                    # Inverser car BM25 plus négatif = meilleur
                    fts_results[rowid] = 1.0 - ((rank - min_rank) / range_rank)
        except Exception:
            # Si la requête FTS échoue (syntaxe invalide), on continue avec les vecteurs
            pass

        # ─── Couche 2 : Embeddings / Cosine Similarity ──────────────
        query_embedding = self._embed_text(query, is_query=True)

        # ─── Fusion des scores ───────────────────────────────────────
        for doc_id, filename, chunk_index, content, embedding_blob in all_docs:
            fts_score = fts_results.get(doc_id, 0.0)
            vec_score = 0.0

            if query_embedding and embedding_blob:
                try:
                    doc_embedding = json.loads(embedding_blob.decode("utf-8"))
                    vec_score = cosine_similarity(query_embedding, doc_embedding)
                except Exception:
                    pass

            # Score hybride pondéré
            if query_embedding:
                final_score = FTS_WEIGHT * fts_score + VECTOR_WEIGHT * vec_score
            else:
                # Pas d'embeddings disponibles → FTS5 uniquement
                final_score = fts_score

            if final_score > 0.01:  # Seuil minimum
                doc_key = f"{filename}#c{chunk_index}"
                scores[doc_key] = {
                    "filename": filename,
                    "chunk_index": chunk_index,
                    "content": content,
                    "score": final_score,
                    "fts_score": fts_score,
                    "vec_score": vec_score,
                }

        # Trier par score décroissant et retourner les top_k
        ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

    # ─── Embeddings Gemini (REST + OAuth CLI) ───────────────────────

    def _embed_text(self, text: str, is_query: bool = False) -> Optional[list[float]]:
        """
        Génère un embedding vectoriel via l'API Gemini.
        Priorité à l'authentification OAuth du Gemini CLI pour une parité OpenClaw.
        """
        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        truncated = text[:2000]

        # On utilise directement REST car il supporte nativement le Token Bearer du CLI
        return _embed_via_rest(truncated, task_type)

    # ─── Méthode fallback (chargement brut) ──────────────────────────

    def load_all_facts(self, max_total_chars: int = 6000) -> str:
        """
        Fallback : charge tout le contenu des faits brut (comme avant V2.0).
        Utilisé quand la recherche hybride échoue complètement.
        """
        if not self.facts_dir.exists():
            return ""
        parts = []
        total = 0
        for f in sorted(self.facts_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                content = f.read_text(encoding="utf-8").strip()
                if total + len(content) > max_total_chars:
                    parts.append(f"\n[...{f.name} tronqué, budget mémoire atteint]")
                    break
                parts.append(f"### 📄 {f.name}\n{content}")
                total += len(content)
        return "\n\n".join(parts)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
