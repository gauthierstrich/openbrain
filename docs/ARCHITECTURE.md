# Architecture Reference (V2.5 — Obsidian Native)

Ce document décrit l'architecture technique d'OpenBrain V2.5. Il met l'accent sur la structure "Local-First" et le système de mémoire hybride.

---

## 1. La Hiérarchie Cognitive (Filesystem)

OpenBrain repose sur une structure de fichiers stricte, conçue pour être compatible avec **Obsidian** et lisible par n'importe quel LLM.

### Structure d'un Agent (V2.5)

```text
agents/<agent-id>/
├── 📓 01 - Journal/         # Journaux quotidiens (YYYY-MM-DD.md)
│                             # Utilise les Callouts Obsidian [!CHAT]
├── 🧠 02 - Mémoire/         # Fiches de faits durables (Wikilinks autorisés)
├── ⚙️ 03 - Configuration/   # L'identité fonctionnelle de l'agent
│   ├── soul.md               # Mission, personnalité, contraintes
│   ├── user.md               # Préférences d'interaction spécifiques
│   └── index.md              # Carte de visite (YAML metadata)
└── 04 - Archives/           # Historique technique
    ├── history/              # JSON rolling history + summary.txt
    └── memory_index.db       # Index SQLite FTS5 (Recherche hybride)
```

---

## 2. Le Moteur Cognitif (Brain Engine)

Le `Brain` (`core/brain.py`) est l'orchestrateur. À chaque message reçu, il suit ce processus :

1.  **Récupération de l'Identité** : Lecture de `identity/user.md` (Global) et `user.md` (Agent).
2.  **Recherche Hybride** : L'indexeur (`memory_index.py`) effectue une recherche simultanée via **SQLite FTS5** (mots-clés) et **Embeddings** (conceptuel).
3.  **Construction du Contexte** : Assemblage dynamique du prompt (Soul + User Global + User Agent + Mémoire + Journaux récents + Historique).
4.  **Inférence Native** : Appel du **Gemini CLI** en mode YOLO (`-y`). Le CLI a accès au système de fichiers et peut exécuter des outils nativement.
5.  **Persistance** : Enregistrement de la réponse dans l'historique et mise à jour du journal quotidien.

---

## 3. Système de Mémoire Hybride (V2.5)

### Recherche Sémantique & OAuth Bridge
OpenBrain utilise les embeddings `text-embedding-004` de Google. 
- **Authentification** : Le système ponte directement sur votre session terminal (`~/.gemini/oauth_creds.json`). Aucune clé API `GOOGLE_API_KEY` n'est requise si vous êtes connecté via le CLI.
- **Scoring** : Les résultats sont pondérés (FTS5 35% / Vecteurs 65%) pour assurer une pertinence maximale, même sur des mots-clés techniques.

---

## 4. Onboarding & Session de Biographie

Nouveauté V2.5 : L'agent **Architecte** possède une mission de "profilage". 
Au premier lancement, il détecte si `identity/user.md` est vide. Il engage alors une discussion pour comprendre vos objectifs. Il utilise ensuite sa capacité système native pour écrire les résultats dans le fichier global, créant ainsi la base de connaissances partagée par tous les futurs agents.

---

## 5. Sécurité : Le Gardien de Code (Code Guard)

Pour garantir la stabilité du système lors des modifications de code par l'IA :
- Toute écriture de fichier `.py` est d'abord effectuée dans un fichier temporaire.
- `core/code_guard.py` valide la syntaxe Python via `py_compile`.
- Si la syntaxe est correcte, une sauvegarde `.bak` du fichier original est créée avant l'écrasement.
- En cas d'erreur de syntaxe, la modification est annulée.

---

*OpenBrain Core V2.5 — Ingénierie pour l'Autonomie et la Souveraineté.*
