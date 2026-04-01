#!/usr/bin/env python3
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Paths
ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

raw_storage = os.getenv("BRAIN_STORAGE_PATH", str(Path.home() / "Documents/Second Brain/OpenBrain"))
STORAGE_ROOT = Path(os.path.expanduser(raw_storage))
AGENT_DIR = STORAGE_ROOT / "Assistant_Personnel"
OUTPUT_FILE = AGENT_DIR / "Souvenirs" / "Faits" / "agenda_devoirs.md"

def get_all_list_names():
    script = 'tell application "Reminders" to get name of every list'
    try:
        res = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=5)
        names = res.stdout.strip()
        if not names:
            return []
        return [n.strip() for n in names.split(', ')]
    except:
        return []

def get_all_uncompleted_reminders():
    """Récupère TOUS les rappels non terminés, de TOUTES les listes, sans bloquer (timeout par liste)."""
    list_names = get_all_list_names()
    if not list_names:
        print("Erreur : Impossible de lire les listes Apple.")
        return []
        
    all_tasks = []
    
    for l_name in list_names:
        l_name_safe = l_name.replace('\\', '\\\\').replace('"', '\\"')
        
        script = f'''
        set out to ""
        tell application "Reminders"
            try
                set theReminders to every reminder of list "{l_name_safe}" whose completed is false
                repeat with r in theReminders
                    set d to "Pas de date"
                    try
                        if due date of r is not missing value then set d to (due date of r as string)
                    end try
                    set out to out & (name of r) & " | " & d & "\\n"
                end repeat
            end try
        end tell
        return out
        '''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT sur la liste {l_name}. Ignoré.")
            continue
        except Exception as e:
            print(f"Erreur sur {l_name}: {e}")
            continue

        output = result.stdout.strip()
        if output:
            for line in output.split('\n'):
                if " | " in line:
                    parts = line.split(" | ")
                    if len(parts) >= 2:
                        all_tasks.append({
                            "matiere": l_name,
                            "titre": parts[0],
                            "echeance": parts[1]
                        })

    return all_tasks

def sync():
    # Détection de la plateforme
    if sys.platform != "darwin":
        print("ℹ️ Synchronisation Apple interrompue : Ce système n'est pas macOS.")
        return 0

    print(f"Début de la synchro dynamique à {datetime.now().strftime('%H:%M:%S')}")
    all_tasks = get_all_uncompleted_reminders()
    
    # ... rest of the function continues correctly ...


if __name__ == "__main__":
    count = sync()
    print(f"Sync dynamique terminé : {count} rappels trouvés.")
