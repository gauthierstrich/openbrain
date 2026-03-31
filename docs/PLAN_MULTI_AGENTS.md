# 🧠 Plan Multi-Agents Personnel — Session du 30 Mars 2026
> Réflexion complète menée avec Antigravity (IA) sur l'architecture d'un système d'agents personnels.

---

## 1. Contexte & Point de Départ

### Ce qu'on voulait comprendre
Le projet de départ était **OpenClaw** (https://github.com/openclaw/openclaw), un framework d'agent IA open-source. La question fondamentale était :

> *"Comment est-ce possible de donner une conscience et une mémoire à un LLM développé par Google, vu que par défaut il ne peut pas lire mes fichiers ?"*

---

## 2. Comment Fonctionne un Agent IA — Les Bases

### Le LLM seul est "aveugle"
Un modèle comme Gemini ou Claude est purement prédictif. À chaque message, il repart de zéro. Il ne sait pas qu'un fichier existe sur ton disque dur si personne ne lui en parle.

### Les 3 composantes d'un vrai agent
Un agent IA n'est pas juste le LLM. C'est un **système en 3 parties** :

| Composante | Rôle | Analogie |
|---|---|---|
| **Le Cerveau (LLM)** | Raisonne, génère du texte | Le décideur |
| **Le Corps (Orchestrateur)** | Lit les fichiers, exécute les commandes, envoie les requêtes API | Le secrétaire |
| **La Mémoire (Fichiers)** | Stocke les souvenirs, la personnalité, l'historique | Les dossiers du bureau |

### La boucle complète d'un message (exemple Telegram + OpenClaw)
```
1. Tu écris "Salut" sur Telegram
2. OpenClaw intercepte le message (Webhook)
3. Il prépare un "Burger de texte" pour Gemini :
   ├── Pain du haut = SOUL.md (qui est l'agent, sa personnalité)
   ├── Viande       = MEMORY.md (les souvenirs importants)
   └── Fromage      = Ton message "Salut"
4. Il envoie ce bloc à Gemini via l'API
5. Gemini répond : "Salut ! Je me souviens qu'hier..."
6. OpenClaw enregistre la réponse dans history.json
7. Il renvoie la réponse sur Telegram
```

> **Conclusion clé :** Gemini n'a PAS de mémoire magique. C'est l'orchestrateur qui lui "rappelle" sa vie à chaque message.

### Pourquoi mon fichier mémoire.txt ne marche pas tout seul
Si tu crées un fichier sur ton Mac, Gemini ne le verra jamais — car **personne ne lui a donné le "corps"** (le code) pour aller le chercher. OpenClaw fournit ce corps.

---

## 3. Comparaison des Solutions de Mémoire (Mars 2026)

| Solution | Type | Meilleur Usage | Inconvénient |
|---|---|---|---|
| **OpenClaw** | Application prête à l'emploi | Agent personnel local, fichiers Markdown | Complexe à modifier en profondeur |
| **Letta (MemGPT)** | Runtime agent | Agent qui gère sa mémoire comme un OS (RAM vs Disque) | Courbe d'apprentissage élevée |
| **Gemini Long Context** | Capacité modèle (2M tokens) | Analyse globale d'un gros projet/document | Coûteux à grande échelle |
| **LangGraph** | Framework développeur | Workflows complexes multi-agents | Nécessite du code sur-mesure |

### Verdict pour notre projet
- **Court terme :** Gemini CLI (déjà installé, natif Google, sans clé API à gérer)
- **Long terme :** Construire son propre orchestrateur léger autour du CLI

---

## 4. Comment Fonctionne Gemini CLI

### Ce qu'on a découvert en lançant `gemini -h`
Gemini CLI est bien plus qu'un simple chatbot en ligne de commande. Il dispose de :

| Commande | Utilité pour notre projet |
|---|---|
| `gemini skills` | Créer des "spécialisations" comportementales par matière |
| `gemini mcp` | Connecter l'agent à des outils externes |
| `gemini hooks` | Déclencher des actions automatiquement |
| `--resume` | Reprendre une session précédente (mémoire de base) |
| `-p / --prompt` | Mode non-interactif → utilisable depuis un script Python |

### Ce qu'est vraiment un "Skill"
Un **Skill** n'est PAS un outil technique (le CLI peut déjà lire les fichiers, les rappels, le calendrier nativement).

Un Skill = un **fichier d'instructions spécialisées** (`SKILL.md`) qui dit à l'agent :
> *"Quand l'utilisateur parle de MT28, voici exactement comment tu dois structurer ta réponse, quels fichiers lire en priorité, et quelle méthode pédagogique suivre."*

C'est une **spécialisation comportementale**, pas un outil.

> Exemple : Le seul Skill installé actuellement est `skill-creator` [Built-in] — un guide pour créer d'autres Skills.

---

## 5. Vision Finale : Architecture Multi-Agents

### La hiérarchie des agents

```
         ┌──────────────────────────────────────┐
         │         AGENT PRINCIPAL (AP)         │
         │  - Connaît toute la vie de Gauthier  │
         │  - Accès complet au Mac              │
         │  - Planifie tâches & emploi du temps │
         │  - Orchestre tous les sous-agents    │
         └───┬──────┬──────┬──────┬────────────┘
             │      │      │      │
          ┌──┘   ┌──┘   ┌──┘   ┌──┘
          ▼      ▼      ▼      ▼
        MT28   PS28   SQ20   LE02  (+ autres matières)
         (un Skill spécialisé par matière UTBM)
```

### Ce que fait chaque agent

**Agent Principal :**
- Connaît tes objectifs de vie (carrière Quant Fund Manager, UTBM, projets)
- Accède à ton calendrier, tes fichiers, tes rappels Mac
- Lit les rapports des agents matières
- Planifie automatiquement les sessions de révision
- Répond aux questions du quotidien

**Agents Matières (un par matière) :**
- Connaît le plan de cours, le style du prof, les méthodes attendues
- Mémorise tes erreurs fréquentes et tes points forts
- Suit ta progression chapitre par chapitre
- Après chaque session, écrit un rapport pour l'Agent Principal

### La communication inter-agents
Via un fichier partagé `agent_status.json` :
```json
{
  "last_update": "2026-03-30T22:00:00",
  "agent_maths_MT28": {
    "derniere_session": "2026-03-30",
    "sujet": "Méthode des bilans - TD1 Ex7",
    "duree_minutes": 45,
    "taches_restantes": ["TD2 Ex3", "Révision Cauchy-Lipschitz"],
    "difficulte": "Haute"
  }
}
```
L'Agent Principal lit ce fichier à chaque démarrage pour organiser ta journée.

---

## 6. Stack Technique Choisie

| Composant | Technologie | Justification |
|---|---|---|
| **Runtime agent** | Gemini CLI | Déjà installé, natif Google, pas de clé API à gérer |
| **Mémoire** | Fichiers Markdown + JSON | Lisibles & éditables par un humain, inspecte les données facilement |
| **Specialisation** | Gemini CLI Skills (SKILL.md) | S'intègre nativement dans le CLI |
| **Orchestration légère** | Python (scripts simples) | Léger, idéal pour lire/écrire des fichiers et coller les morceaux |
| **Modèle** | Gemini 3 Flash / 3.1 Pro | Calculs sur serveurs Google, ton PC ne fait que de la "logistique" |

### Pourquoi Python est le bon choix ici
Ton script Python ne fait **que de la logistique** (lire/écrire des fichiers, envoyer des requêtes HTTP légères). 100% de la puissance de calcul est sur les serveurs Google. Python est donc parfaitement adapté : simple, lisible, et excellent pour la gestion de fichiers.

---

## 7. Architecture des Fichiers (à créer)

```
~/Desktop/OpenBrain/
├── agents/
│   ├── personal/
│   │   ├── SOUL.md            ← Personnalité, règles, priorités de l'agent
│   │   ├── MEMORY.md          ← Index des souvenirs importants
│   │   ├── USER.md            ← Profil de Gauthier (UTBM, objectifs...)
│   │   └── memory/
│   │       ├── daily/         ← Journal quotidien (2026-03-30.md)
│   │       ├── projects/      ← Projets en cours
│   │       └── facts/         ← Faits permanents sur ta vie
│   └── maths/
│       ├── SOUL.md            ← Spécialisation UTBM (style "SI...ALORS...")
│       ├── MT28/
│       │   ├── SKILL.md       ← Instructions spécifiques MT28
│       │   ├── progression.md ← Où tu en es dans le cours
│       │   └── erreurs.md     ← Tes erreurs fréquentes mémorisées
│       ├── PS28/
│       ├── SQ20/
│       └── LE02/
└── shared/
    └── agent_status.json      ← Fichier de communication inter-agents
```

---

## 8. Plan de Progression en 3 Phases

### Phase 1 — Fondations de l'Agent Principal (2-3 semaines)
- [ ] Créer la structure de fichiers ci-dessus
- [ ] Rédiger le `SOUL.md` de l'Agent Principal ensemble
- [ ] Rédiger `USER.md` (profil complet de Gauthier)
- [ ] Tester des vraies conversations et itérer sur la mémoire
- [ ] Créer le Skill `skill-creator` pour les agents matières

### Phase 2 — Agents Matières UTBM (1-2 semaines)
- [ ] Créer le SOUL.md de l'Agent Maths (rigueur, SI...ALORS...)
- [ ] Créer les SKILL.md pour MT28, PS28, SQ20, LE02
- [ ] Construire la base de connaissances des cours
- [ ] Implémenter le système de reporting post-session

### Phase 3 — Interconnexion & Orchestration (1 semaine)
- [ ] L'Agent Principal lit `agent_status.json` au démarrage
- [ ] Il planifie les révisions dans le calendrier Mac automatiquement
- [ ] Interface unifiée pour choisir avec quel agent parler

---

## 9. Questions Ouvertes

Ces points sont à décider avant de commencer à coder :

1. **Interface :** Terminal Mac uniquement pour l'instant, ou Telegram/Discord dès le début ?
2. **Mémoire vie perso :** Quel niveau de détail mettre dans USER.md ? (emploi du temps, objectifs financiers, projets personnels...)
3. **Confidentialité :** Les fichiers seront en clair sur ton Mac — acceptable ?
4. **Disponibilité :** L'agent tourne en fond en permanence, ou seulement quand tu le lances ?

---

## 10. Insight Clé de la Session

> **La preuve que le système fonctionne déjà :**
> Antigravity (l'IA) connaissait les matières de Gauthier (MT28, PS28, SQ20, LE02) sans qu'il les ait mentionnées dans cette session. Pourquoi ? Parce qu'Antigravity lit des "résumés de conversations passées" au début de chaque session — exactement le même mécanisme que celui qu'on veut reproduire pour l'Agent Principal via des fichiers MEMORY.md.

---

*Document créé le 30 mars 2026 — Session de réflexion avec Antigravity*
*Prochaine étape : répondre aux 4 questions ouvertes et commencer la Phase 1*
