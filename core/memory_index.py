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
EMBED_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent"

# ─── Tentative d'import du SDK Gemini (optionnel) ───────────────────
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
    """Appelle l'API Gemini Embeddings via REST avec une API Key.
    Utilisé quand le SDK google-genai n'est pas installé."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    payload = json.dumps({
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {"parts": [{"text": text[:2000]}]},
        "outputDimensionality": EMBEDDING_DIM,
        "taskType": task_type,
    }).encode("utf-8")

    url = f"{EMBED_API_URL}?key={api_key}"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        ctx = _get_ssl_context()
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read())
            return data["embedding"]["values"]
    except Exception:
        return None


def _init_genai_client():
    """Initialise le client GenAI avec une API Key. Retourne None si pas de clé."""
    global _genai_client
    if _genai_client is not None:
        return _genai_client

    if not _genai_available:
        return None

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        _genai_client = genai.Client(api_key=api_key)
        return _genai_client
    except Exception:
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calcule la similarité cosinus entre deux vecteurs."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


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
        conn.executescript("""
            -- Table principale des documents indexés
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding BLOB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    def index_facts(self) -> dict:
        """
        Scanne memory/facts/ et (ré)indexe les fichiers modifiés.
        Retourne un rapport {indexed: int, skipped: int, removed: int}.
        """
        if not self.facts_dir.exists():
            return {"indexed": 0, "skipped": 0, "removed": 0}

        conn = self._get_conn()
        report = {"indexed": 0, "skipped": 0, "removed": 0}

        # Fichiers actuellement sur disque
        disk_files = {}
        for f in self.facts_dir.iterdir():
            if f.is_file() and f.suffix == ".md":
                content = f.read_text(encoding="utf-8").strip()
                content_hash = hashlib.md5(content.encode()).hexdigest()
                disk_files[f.name] = (content, content_hash)

        # Fichiers actuellement dans l'index
        indexed = {
            row[0]: row[1]
            for row in conn.execute("SELECT filename, content_hash FROM documents")
        }

        # Supprimer les fichiers disparus du disque
        for filename in indexed:
            if filename not in disk_files:
                conn.execute("DELETE FROM documents WHERE filename = ?", (filename,))
                report["removed"] += 1

        # Indexer les fichiers nouveaux ou modifiés
        for filename, (content, content_hash) in disk_files.items():
            if filename in indexed and indexed[filename] == content_hash:
                report["skipped"] += 1
                continue

            # Générer l'embedding (optionnel)
            embedding_blob = None
            embedding = self._embed_text(content)
            if embedding:
                embedding_blob = json.dumps(embedding).encode("utf-8")

            if filename in indexed:
                # Mise à jour
                conn.execute(
                    "UPDATE documents SET content=?, content_hash=?, embedding=?, updated_at=CURRENT_TIMESTAMP WHERE filename=?",
                    (content, content_hash, embedding_blob, filename),
                )
            else:
                # Insertion
                conn.execute(
                    "INSERT INTO documents (filename, content, content_hash, embedding) VALUES (?, ?, ?, ?)",
                    (filename, content, content_hash, embedding_blob),
                )
            report["indexed"] += 1

        conn.commit()
        return report

    # ─── Recherche hybride ───────────────────────────────────────────

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        """
        Recherche hybride : FTS5 (BM25) + Embeddings (Cosine Similarity).
        Retourne les top_k résultats les plus pertinents.

        Returns:
            Liste de dicts : [{filename, content, score}, ...]
        """
        conn = self._get_conn()

        # S'assurer que l'index est à jour
        self.index_facts()

        # Tous les documents
        all_docs = list(conn.execute(
            "SELECT id, filename, content, embedding FROM documents"
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
        for doc_id, filename, content, embedding_blob in all_docs:
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
                scores[filename] = {
                    "filename": filename,
                    "content": content,
                    "score": final_score,
                    "fts_score": fts_score,
                    "vec_score": vec_score,
                }

        # Trier par score décroissant et retourner les top_k
        ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

    # ─── Embeddings Gemini (Cascade : SDK → REST/OAuth → None) ────────

    def _embed_text(self, text: str, is_query: bool = False) -> Optional[list[float]]:
        """
        Génère un embedding vectoriel via l'API Gemini.
        Stratégie en cascade :
          1. SDK google-genai (si GOOGLE_API_KEY est défini)
          2. REST API directe avec le token OAuth du Gemini CLI
          3. None (dégradation gracieuse → FTS5 uniquement)
        """
        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        truncated = text[:2000]

        # Stratégie 1 : SDK avec API Key
        client = _init_genai_client()
        if client is not None:
            try:
                response = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=truncated,
                    config=genai_types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=EMBEDDING_DIM,
                    ),
                )
                return response.embeddings[0].values
            except Exception:
                pass

        # Stratégie 2 : REST API avec OAuth token du Gemini CLI
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
