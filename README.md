# OpenBrain — V2.5 (Obsidian Edition)

> Transformez votre connaissance personnelle en une intelligence autonome et évolutive — hébergée localement, structurée pour Obsidian.

[![Status: v2.5](https://img.shields.io/badge/Status-v2.5%20Stable-green)]()
[![Structure: Obsidian](https://img.shields.io/badge/Structure-Obsidian%20Native-purple)]()

---

## 🌟 La Vision OpenBrain

OpenBrain n'est pas un simple assistant. C'est un **système d'exploitation cognitif** construit sur un principe fondamental : **Votre identité vous appartient.**

Contrairement aux IA cloud qui oublient tout après chaque session, OpenBrain construit une mémoire persistante et structurée en Markdown. La version 2.5 introduit le concept de **Profil Biographique Global** : vos agents savent qui vous êtes, quels sont vos objectifs de vie et comment vous aider au mieux, dès la première seconde.

---

## 🚀 Nouveau Flux d'Installation (V2.5)

L'installation est devenue conversationnelle. Le terminal ne sert qu'à poser les fondations techniques.

```bash
# 1. Clone & Setup
git clone https://github.com/gauthierstrich/openbrain.git
cd openbrain

# 2. Onboarding Interactif
bash scripts/ob-init.sh
```

**Ce qui se passe maintenant :**
1. `ob-init.sh` vous demande votre prénom et configure vos accès Telegram.
2. Vous lancez l'OS (`python3 scripts/ob-start.py`).
3. **L'Architecte** vous accueille sur Telegram par votre prénom.
4. Il lance une **Session de Biographie** pour remplir votre profil global (`identity/user.md`).
5. Une fois votre identité définie, il vous aide à déployer vos agents spécialistes.

---

## 🧠 Architecture de la Mémoire (Obsidian V2.5)

Chaque agent est désormais un dossier **Obsidian-Ready**, structuré pour une lisibilité humaine maximale :

```text
agents/<nom-agent>/
├── 📓 01 - Journal/         # Traces quotidiennes (Callouts Obsidian)
├── 🧠 02 - Mémoire/         # Faits durables & connaissances (Wikilinks)
├── ⚙️ 03 - Configuration/   # Soul.md (Âme) et User.md (Préférences)
└── 04 - Archives/           # Historique technique & Index de recherche
```

### Le Profil Global (`identity/user.md`)
Situé à la racine de votre Second Cerveau, ce fichier est la **Source de Vérité** de votre identité. Tous vos agents le lisent. Si vous changez de métier ou d'objectif de vie, modifiez ce fichier : tous vos agents s'adapteront instantanément.

---

## 🛠️ Caractéristiques Techniques

- **Recherche Hybride (V2.5)** : Combine la puissance du plein texte (SQLite FTS5) et de la sémantique (Embeddings Gemini) pour un rappel instantané.
- **Zéro-Config Auth** : Utilise votre session OAuth existante via Gemini CLI. Pas de clés API à gérer manuellement.
- **Code Guard** : Un gardien intégré vérifie la syntaxe de chaque modification de code effectuée par les agents pour éviter tout crash du système.
- **Local-First** : Vos données restent en Markdown. Pas de base de données propriétaire, pas de cloud.

---

## 🏗️ Structure du Projet

- `core/` : Le moteur cognitif (`brain.py`) et l'indexeur hybride.
- `agents/` : Vos instances d'agents (Architecte, Assistant Personnel, etc.).
- `scripts/` : Outils d'initialisation et de gestion.
- `template/` : Les gènes originels pour la création de nouveaux agents.

---

*OpenBrain est sous licence MIT. Votre intelligence est à vous.*
