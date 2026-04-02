import subprocess
import sys
from datetime import datetime

class AppleSyncError(Exception):
    pass

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
    if sys.platform != "darwin":
        raise AppleSyncError("La synchronisation Apple Rappels nécessite macOS.")
        
    list_names = get_all_list_names()
    if not list_names:
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
                    set out to out & (name of r) & " | " & d & "\n"
                end repeat
            end try
        end tell
        return out
        '''
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=15)
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
        except Exception:
            pass

    return all_tasks

def sync():
    return get_all_uncompleted_reminders()
