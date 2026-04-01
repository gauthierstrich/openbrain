#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from dotenv import load_dotenv

# Repertoires fondamentaux
ROOT = Path(__file__).resolve().parent.parent
RESTART_SIGNAL = ROOT / "restart.signal"

class BotSupervisor:
    def __init__(self):
        self.processes = {}
        self.running = True
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

    def load_env(self):
        load_dotenv(ROOT / ".env", override=True)

    def get_active_agents(self):
        self.load_env()
        raw_storage = os.getenv("BRAIN_STORAGE_PATH")
        if not raw_storage:
            print("❌ Erreur : BRAIN_STORAGE_PATH non trouvé dans le .env")
            return []
            
        storage_root = Path(os.path.expanduser(raw_storage))
        agents_dir = storage_root / "agents"
        
        if not agents_dir.exists():
            print(f"❌ Erreur : Dossier agents introuvable dans {agents_dir}")
            return []
        
        active = []
        for d in agents_dir.iterdir():
            if not d.is_dir() or d.name.startswith(("_", ".")):
                continue
            
            token_var = f"TELEGRAM_TOKEN_{d.name.upper()}"
            if os.getenv(token_var):
                active.append(d.name)
        return active

    def start_bots(self):
        agents = self.get_active_agents()
        
        if not agents:
            print("⚠️ Aucun agent actif trouvé (vérifiez les TOKENS dans le .env)")
            return

        print(f"\n🚀 [SUPERVISEUR] Lancement des agents : {', '.join(agents)}")
        
        for name in agents:
            if name not in self.processes or self.processes[name].poll() is not None:
                print(f"✅ Démarrage de {name}...")
                p = subprocess.Popen(
                    [sys.executable, "-m", "core.interfaces.telegram", name],
                    cwd=str(ROOT)
                )
                self.processes[name] = p

    def stop_bots(self):
        print("\n🛑 [SUPERVISEUR] Arrêt de tous les agents...")
        for name, p in self.processes.items():
            p.terminate()
        self.processes = {}

    def stop(self, signum, frame):
        self.running = False
        self.stop_bots()
        sys.exit(0)

    def run(self):
        print(f"✨ OpenBrain Supervisor V1.0 - Racine : {ROOT}")
        self.start_bots()
        
        while self.running:
            # Vérifier si un signal de redémarrage est présent
            if RESTART_SIGNAL.exists():
                print("\n🔄 [SIGNAL] Détection d'un nouveau membre. Re-chargement du système...")
                RESTART_SIGNAL.unlink()
                self.stop_bots()
                time.sleep(2)
                self.start_bots()
            
            # Vérifier la santé des processus
            for name, p in list(self.processes.items()):
                if p.poll() is not None:
                    print(f"⚠️ Agent {name} s'est arrêté. Relancement imminent...")
                    self.start_bots()
            
            time.sleep(3)

if __name__ == "__main__":
    supervisor = BotSupervisor()
    supervisor.run()
