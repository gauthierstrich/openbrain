#!/bin/bash
# OpenBrain Core — Universal Ghost Installer
set -e

BLUE='\033[0;34m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}------------------------------------------------${NC}"
echo -e "🚀 OPENBRAIN CORE — SETUP ARCHITECTE"
echo -e "${BLUE}------------------------------------------------${NC}"

# 1. Doctor
echo -e "🔍 Vérification système..."
if ! bash "$DIR/scripts/ob-doctor.sh"; then
    exit 1
fi

# 2. Setup
echo -e "\n📝 Configuration Onboarding"
read -p "👋 Comment t'appelles-tu ? : " USER_NAME
read -p "👤 Ton ID Telegram (ex: 123456) : " ALLOWED_USER_ID
echo -e "\n🔑 Pour commencer, tu as besoin d'un Token Bot (@BotFather) pour ton Architecte."
read -p "Token de l'Architecte : " ARCH_TOKEN

DEFAULT_STORAGE="$HOME/Documents/OpenBrain"
read -p "📂 Où stocker ton Second Cerveau ? [$DEFAULT_STORAGE] : " RAW_STORAGE
STORAGE_PATH=${RAW_STORAGE:-$DEFAULT_STORAGE}
STORAGE_PATH="${STORAGE_PATH/#\~/$HOME}"

# 3. Copies Templates (Global Structure)
echo -e "\n🏗️ Initialisation de la structure..."
mkdir -p "$STORAGE_PATH/agents"
mkdir -p "$STORAGE_PATH/identity"
cp -R "$DIR/template/identity/"* "$STORAGE_PATH/identity/"

# 4. Personnalisation immédiate du profil global
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' "s/{{USER_NAME}}/$USER_NAME/g" "$STORAGE_PATH/identity/user.md"
else
  sed -i "s/{{USER_NAME}}/$USER_NAME/g" "$STORAGE_PATH/identity/user.md"
fi

# 5. Installation de l'Architecte
echo "Injecting Architect DNA..."
cp -R "$DIR/template/agents/architect" "$STORAGE_PATH/agents/"

# 6. Env setup
cat > "$DIR/.env" << ENVFILE
GEMINI_MODEL=gemini-3-flash-preview
USER_LANGUAGE=fr
BRAIN_STORAGE_PATH="$STORAGE_PATH"
ALLOWED_USER_ID=$ALLOWED_USER_ID
TELEGRAM_TOKEN_ARCHITECT=$ARCH_TOKEN
ENVFILE

# 7. Obsidian Starter
mkdir -p "$STORAGE_PATH/.obsidian"
cp -R "$DIR/.obsidian_starter/"* "$STORAGE_PATH/.obsidian/"

# 8. Deps
echo -e "\n📦 Installation des librairies..."
pip3 install -r "$DIR/requirements.txt" --quiet

echo -e "\n${GREEN}✨ CONFIGURATION TERMINÉE ! ✨${NC}"
echo -e "Merci $USER_NAME. Le terminal est maintenant inutile."
echo -e "${CYAN}👉 Lance cette commande pour activer ton OS :${NC}"
echo -e "python3 scripts/ob-start.py"
echo -e "\nOuvre ensuite Telegram et envoie /start à ton Architecte."
