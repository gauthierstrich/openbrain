#!/bin/bash

# OpenBrain Setup Script 🧠
# Standards: Google Engineering

set -e

echo "------------------------------------------------"
echo "🚀 Initialisation de l'environnement OpenBrain"
echo "------------------------------------------------"

# 1. Vérification Python
if ! command -v python3 &> /dev/null
then
    echo "❌ Erreur : Python3 n'est pas installé."
    exit 1
fi

# 2. Installation des dépendances
echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt --quiet

# 3. Vérification Gemini CLI
if ! command -v gemini &> /dev/null
then
    echo "⚠️ Warning : 'gemini-cli' n'est pas détecté dans ton PATH."
    echo "   Assure-toi de l'installer via : https://github.com/google-gemini/gemini-cli"
fi

# 4. Préparation du fichier .env
if [ ! -f .env ]; then
    echo "📄 Création du fichier .env à partir de l'exemple..."
    cp .env.example .env
    echo "✅ .env créé. N'oublie pas de le remplir avec tes clés !"
else
    echo "✅ Fichier .env déjà présent."
fi

# 5. Initialisation de la structure du Second Brain (si configuré localement)
# On récupère le chemin depuis le .env (ou défaut)
STORAGE_PATH=$(grep "BRAIN_STORAGE_PATH" .env | cut -d '=' -f2 | sed 's/"//g' | sed "s|~|$HOME|")

if [ -z "$STORAGE_PATH" ]; then
    STORAGE_PATH="$HOME/Documents/Second Brain/OpenBrain"
fi

echo "📁 Initialisation de la structure dans : $STORAGE_PATH"
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Identité"
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Souvenirs/Faits"
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Souvenirs/Journal"
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Souvenirs/Historique"

echo "------------------------------------------------"
echo "✨ Setup terminé avec succès !"
echo "Utilise 'python3 src/main_telegram.py' pour lancer le bot."
echo "------------------------------------------------"
