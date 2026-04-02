#!/usr/bin/env python3
import os
import sys
import shutil
from pathlib import Path
from core.brain import Brain
from core import config
from core.agent_creator import AgentCreator, AgentCreationError

VERSION = "Core V0.1"

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    BLUE1   = "\033[38;5;69m"
    BLUE2   = "\033[38;5;75m"
    CYAN    = "\033[38;5;80m"
    PINK    = "\033[38;5;175m"
    MAGENTA = "\033[38;5;168m"
    YELLOW  = "\033[38;5;222m"
    GREEN   = "\033[38;5;114m"
    RED     = "\033[38;5;203m"
    WHITE   = "\033[38;5;255m"
    GRAY    = "\033[38;5;245m"

def get_terminal_width():
    return shutil.get_terminal_size((80, 24)).columns

def strip_ansi(text: str):
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)

def draw_box(lines: list[str], color: str = C.YELLOW):
    w = get_terminal_width() - 2
    box = f"{color}╭{'─' * w}╮{C.RESET}\n"
    for line in lines:
        visible_len = len(strip_ansi(line))
        padding = w - visible_len - 2
        if padding < 0: padding = 0
        box += f"{color}│{C.RESET} {line}{' ' * padding} {color}│{C.RESET}\n"
    box += f"{color}╰{'─' * w}╯{C.RESET}"
    return box

class OpenBrainCLI:
    def __init__(self):
        self.brain = Brain()
        self.creator = AgentCreator()

    def print_banner(self):
        print()
        print(f"       {C.BLUE1}╭───────╮{C.RESET}")
        print(f"      {C.BLUE1}╭╯{C.BLUE2} ·bg·  {C.BLUE1}╰╮{C.RESET}     {C.WHITE}{C.BOLD}OpenBrain{C.RESET} {C.GRAY}v{VERSION}{C.RESET}")
        print(f"     {C.BLUE2}╭╯{C.CYAN}  ╭──╮  {C.BLUE2}╰╮{C.RESET}")
        print(f"     {C.CYAN}│  ╭╯  ╰╮  │{C.RESET}    {C.BOLD}Bienvenue, {config.USER_NAME}{C.RESET}")
        print(f"     {C.CYAN}│  ╰╮  ╭╯  │{C.RESET}    {C.GRAY}Propulsé par{C.RESET} {C.BLUE2}{config.GEMINI_MODEL}{C.RESET}")
        print(f"     {C.PINK}╰╮  ╰──╯  ╭╯{C.RESET}")
        print(f"      {C.PINK}╰╮      ╭╯{C.RESET}")
        print(f"       {C.MAGENTA}╰──────╯{C.RESET}")
        print()
        
        agent = self.brain.get_active_agent()
        if agent:
            status = f"{C.GREEN}●{C.RESET}  {C.WHITE}{C.BOLD}Agent Actif :{C.RESET} {agent.emoji} {agent.name.capitalize()} ({agent.id})"
        else:
            status = f"{C.RED}●{C.RESET}  {C.WHITE}{C.BOLD}Agent Actif :{C.RESET} Aucun."
            
        print(draw_box([status], C.BLUE2))
        print()
        print(f"  {C.GRAY}Commandes :  {C.WHITE}/agents{C.GRAY}  │  {C.WHITE}/switch <nom>{C.GRAY}  │  {C.WHITE}/new-agent{C.GRAY}  │  {C.WHITE}/quit{C.RESET}\n")

    def run(self):
        os.system("clear" if os.name != "nt" else "cls")
        self.print_banner()

        while True:
            try:
                agent = self.brain.get_active_agent()
                prompt_name = agent.id if agent else "core"
                user_input = input(f" {C.BLUE2}{prompt_name} >{C.RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{C.PINK}Mise en veille. À bientôt {config.USER_NAME} !{C.RESET}\n")
                break

            if not user_input: continue

            cmd = user_input.lower().split()
            base_cmd = cmd[0]

            if base_cmd in ("/quit", "/exit", "quit", "exit"):
                print(f"\n{C.PINK}Mise en veille.{C.RESET}\n")
                break
            
            elif base_cmd == "/agents":
                self.brain.refresh_agents()
                print(f"\n{C.CYAN}Agents disponibles :{C.RESET}")
                for key, ag in self.brain.agents.items():
                    print(f"  {ag.emoji} {C.WHITE}{C.BOLD}{key}{C.RESET} — {ag.description}")
                print()
                continue
                
            elif base_cmd == "/switch":
                if len(cmd) < 2:
                    print(f"\n{C.RED}Usage: /switch <nom_agent>{C.RESET}\n")
                    continue
                target = cmd[1]
                if self.brain.set_agent(target):
                    print(f"\n{C.GREEN}✓ Switched to agent '{target}'{C.RESET}\n")
                else:
                    print(f"\n{C.RED}✗ Agent '{target}' non trouvé. Tapez /agents.{C.RESET}\n")
                continue

            elif base_cmd == "/new-agent":
                self.run_creation_wizard()
                continue

            elif base_cmd == "/delete-agent":
                if len(cmd) < 2:
                    print(f"\n{C.RED}Usage: /delete-agent <nom_agent>{C.RESET}\n")
                    continue
                target = cmd[1]
                confirm = input(f"Voulez-vous vraiment supprimer '{target}' ? [y/N] ")
                if confirm.lower() == 'y':
                    try:
                        res = self.creator.delete_agent(target)
                        if res:
                            print(f"\n{C.GREEN}✓ Agent '{target}' placé en corbeille._trash_{C.RESET}\n")
                            self.brain.refresh_agents()
                            self.brain.set_agent("personal")
                        else:
                            print(f"\n{C.RED}✗ Agent introuvable.{C.RESET}\n")
                    except Exception as e:
                        print(f"\n{C.RED}Erreur : {e}{C.RESET}\n")
                continue

            elif base_cmd == "/clear":
                os.system("clear" if os.name != "nt" else "cls")
                self.print_banner()
                continue

            if not self.brain.get_active_agent():
                print(f"\n{C.RED}Veuillez sélectionner un agent avec /switch ou créer un agent avec /new-agent.{C.RESET}\n")
                continue

            # Process Message
            print(f"\n{C.DIM}✦ Réflexion ({config.GEMINI_MODEL})...{C.RESET}\n")
            response = self.brain.process_message(user_input)
            print(f"{C.CYAN}✦{C.RESET} {response}\n")

    def run_creation_wizard(self):
        print(f"\n{C.BLUE2}╭──────────────────────────────────────────────╮{C.RESET}")
        print(f"{C.BLUE2}│{C.RESET}  {C.WHITE}{C.BOLD}🧪 Création d'un nouvel Agent Spécialisé{C.RESET}     {C.BLUE2}│{C.RESET}")
        print(f"{C.BLUE2}╰──────────────────────────────────────────────╯{C.RESET}\n")
        
        name = input("  Nom de l'agent (ex: math) : ").strip().lower()
        if not name: return
        
        emoji = input("  Emoji (ex: 📐) : ").strip() or "🤖"
        specialty = input("  Spécialité (ex: Physique quantique) : ").strip()
        description = input("  Description brève de son caractère : ").strip()
        
        try:
            path = self.creator.create_agent(name, description, specialty, emoji)
            self.brain.refresh_agents()
            print(f"\n{C.GREEN}✅ Agent '{name}' créé avec succès !{C.RESET}")
            print(f"📁 Dossier : {path}")
            print(f"💡 Pour l'utiliser, tapez : /switch {name}\n")
        except AgentCreationError as e:
            print(f"\n{C.RED}❌ Échec de la création : {e}{C.RESET}\n")

if __name__ == "__main__":
    app = OpenBrainCLI()
    app.run()
