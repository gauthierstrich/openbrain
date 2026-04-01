#!/bin/bash

# OpenBrain — Assistant d'Installation Interactif (Wizard) 🧠
# Standards: Multi-OS (macOS & Ubuntu) Excellence
# Author: Antigravity

set -e

# Couleurs pour une sortie "Premium"
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color
echo -e "${BLUE}------------------------------------------------${NC}"
echo -e "🚀 BIENVENUE DANS L'ASSISTANT OPENBRAIN"
echo -e "${BLUE}------------------------------------------------${NC}"

# 1. Vérification des dépendances système
echo -e "🔍 Vérification de ton environnement..."
PYTHON=$(which python3 || echo "python3")
if ! command -v "$PYTHON" &> /dev/null; then
    echo "❌ Erreur : Python3 est requis."
    exit 1
fi

# 2. Gestion du stockage du Second Cerveau
DEFAULT_STORAGE="$HOME/Documents/Second Brain/OpenBrain"
echo -e "\n📁 ${BLUE}Emplacement de ton Second Brain${NC}"
read -p "Où souhaites-tu stocker ton cerveau ? [$DEFAULT_STORAGE] : " USER_STORAGE
STORAGE_PATH=${USER_STORAGE:-$DEFAULT_STORAGE}
# Remplacer ~ par $HOME
STORAGE_PATH="${STORAGE_PATH/#\~/$HOME}"

# 3. Configuration de la sécurité (ID Telegram)
echo -e "\n🛡️ ${BLUE}Sécurité Telegram${NC}"
read -p "Saisis ton ID numérique Telegram (ALLOWED_USER_ID) : " USER_ID

# 4. Configuration des agents (Bot Tokens)
echo -e "\n🤖 ${BLUE}Configuration des Agents (Bot Tokens)${NC}"
read -p "Token de l'Assistant Personnel : " TOKEN_PERSONAL
read -p "Token de l'Agent AC20 (Data Science) : " TOKEN_AC20

# 5. Génération du fichier .env
echo -e "\n�� Génération du fichier .env..."
cat > .env << ENVFILE
# ─── Tokens Telegram (Un par agent) ───
TELEGRAM_TOKEN_PERSONAL=$TOKEN_PERSONAL
TELEGRAM_TOKEN_AC20=$TOKEN_AC20

# ─── Sécurité ───
ALLOWED_USER_ID=$USER_ID

# ─── Stockage ───
BRAIN_STORAGE_PATH="$STORAGE_PATH"
ENVFILE
echo -e "✅ Fichier .env configuré avec succès."

# 6. Installation des dépendances Python
echo -e "\n📦 Installation des bibliothèques nécessaires..."
"$PYTHON" -m pip install -r requirements.txt --quiet
echo -e "✅ Dépendances installées."

# 7. Initialisation de la structure du Second Brain
echo -e "\n🏗️ Initialisation de la structure physique..."
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Identité"
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Souvenirs/Faits"
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Souvenirs/Journal"
mkdir -p "$STORAGE_PATH/Assistant_Personnel/Souvenirs/Historique"
mkdir -p "$STORAGE_PATH/Academie/AC20/Identite"
mkdir -p "$STORAGE_PATH/Academie/AC20/Ressources"
mkdir -p "$STORAGE_PATH/Academie/AC20/Souvenirs/Journal"
mkdir -p "$STORAGE_PATH/Academie/AC20/Souvenirs/Historique"

# Créer les fichiers d'identité minimaux si absents
[ ! -f "$STORAGE_PATH/Assistant_Personnel/Identité/soul.md" ] && echo "# ÂME ASSISTANT PERSONNEL" > "$STORAGE_PATH/Assistant_Personnel/Identité/soul.md"

echo -e "✅ Arborescence créée dans : $STORAGE_PATH"

# 8. Ajout d'alias optionnels (Facultatif)
echo -e "\n🛡️ ${BLUE}Options (Aliases)${NC}"
read -p "Souhaites-tu ajouter un alias 'brain' dans ton terminal ? [y/N] : " ADD_ALIAS
if [[ "$ADD_ALIAS" =~ ^[Yy]$ ]]; then
    # Détection intelligente du profil Shell
    SHELL_PROFILE=""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SHELL_PROFILE="$HOME/.zshrc"
    else
        SHELL_PROFILE="$HOME/.bashrc"
    fi
    
    # Vérifier l'existence du fichier
    if [ ! -f "$SHELL_PROFILE" ]; then
        touch "$SHELL_PROFILE"
    fi
    
    echo "alias brain='cd $(pwd) && bash scripts/start_agents.sh'" >> "$SHELL_PROFILE"
    echo -e "✅ Alias 'brain' ajouté dans $SHELL_PROFILE (redémarre ton terminal ou 'source $SHELL_PROFILE')."
fi

echo -e "\n${GREEN}------------------------------------------------${NC}"
echo -e "✨ CONFIGURATION TERMINÉE ! ✨"
echo -e "${GREEN}------------------------------------------------${NC}"
echo -e "Utilise la commande suivante pour lancer tous tes assistants :"
echo -e "   ${BLUE}bash scripts/start_agents.sh${NC}\n"
