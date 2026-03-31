#!/usr/bin/env python3
"""
OpenBrain — Agent Principal (Version Terminal)
Un orchestrateur léger qui donne une mémoire persistante à Gemini CLI.
Version refactorisée : utilise brain.py pour l'intelligence.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

# Importer l'intelligence partagée
import brain

# ─── Configuration ──────────────────────────────────────────────────
VERSION = "1.5.0"

# ─── Couleurs ANSI (palette Gemini CLI) ───────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ITALIC  = "\033[3m"
    # Couleurs
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
    DARK    = "\033[38;5;240m"
    BLUE    = "\033[38;5;75m"

def get_terminal_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns

def strip_ansi(text: str) -> str:
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)

def draw_box(lines: list[str], color: str = C.YELLOW) -> str:
    w = get_terminal_width() - 2
    box = f"{color}╭{'─' * w}╮{C.RESET}\n"
    for line in lines:
        visible_len = len(strip_ansi(line))
        padding = w - visible_len - 2
        if padding < 0: padding = 0
        box += f"{color}│{C.RESET} {line}{' ' * padding} {color}│{C.RESET}\n"
    box += f"{color}╰{'─' * w}╯{C.RESET}"
    return box

def print_banner():
    print()
    print(f"       {C.BLUE1}╭───────╮{C.RESET}")
    print(f"      {C.BLUE1}╭╯{C.BLUE2} ·bg·  {C.BLUE1}╰╮{C.RESET}     {C.WHITE}{C.BOLD}OpenBrain{C.RESET} {C.GRAY}v{VERSION}{C.RESET}")
    print(f"     {C.BLUE2}╭╯{C.CYAN}  ╭──╮  {C.BLUE2}╰╮{C.RESET}")
    print(f"     {C.CYAN}│  ╭╯  ╰╮  │{C.RESET}    {C.BOLD}Agent Principal{C.RESET} {C.GRAY}— Assistant Personnel{C.RESET}")
    print(f"     {C.CYAN}│  ╰╮  ╭╯  │{C.RESET}    {C.GRAY}Propulsé par{C.RESET} {C.BLUE2}Gemini CLI{C.RESET}")
    print(f"     {C.PINK}╰╮  ╰──╯  ╭╯{C.RESET}")
    print(f"      {C.PINK}╰╮      ╭╯{C.RESET}")
    print(f"       {C.MAGENTA}╰──────╯{C.RESET}")
    print()

    history = brain.load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    daily_exists = (brain.P["daily"] / f"{today}.md").exists()

    status_lines = [
        f"{C.GREEN}●{C.RESET}  {C.WHITE}{C.BOLD}Mémoire :{C.RESET}     {C.CYAN}soul.md{C.RESET} ✓   {C.CYAN}user.md{C.RESET} ✓   {C.CYAN}memory_index.md{C.RESET} ✓",
        f"{C.GREEN}●{C.RESET}  {C.WHITE}{C.BOLD}Historique :{C.RESET}  {C.YELLOW}{len(history)}{C.RESET} échange(s) en mémoire",
        f"{C.GREEN}●{C.RESET}  {C.WHITE}{C.BOLD}Journal :{C.RESET}     {'✅ ' + today + '.md' if daily_exists else '🆕 Nouvelle journée'}",
    ]
    print(draw_box(status_lines, C.YELLOW))
    print()
    print(f"  {C.GRAY}Commandes :  {C.WHITE}/quit{C.GRAY}  quitter  │  {C.WHITE}/status{C.GRAY}  état mémoire  │  {C.WHITE}/clear{C.GRAY}  effacer l'écran{C.RESET}")
    print()

def print_status():
    history = brain.load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log = brain.P["daily"] / f"{today}.md"
    memory_content = brain.read_file(brain.P["index"])
    fact_count = memory_content.count("- ")
    daily_count = len(list(brain.P["daily"].glob("*.md")))

    lines = [
        f"{C.WHITE}{C.BOLD}📊  État de la mémoire{C.RESET}",
        f"",
        f"  {C.CYAN}Fichiers principaux{C.RESET}",
        f"    soul.md           {'✅' if brain.P['soul'].exists() else '❌'}   {C.GRAY}Personnalité de l'agent{C.RESET}",
        f"    user.md           {'✅' if brain.P['user'].exists() else '❌'}   {C.GRAY}Profil de Gauthier{C.RESET}",
        f"    memory_index.md   {'✅' if brain.P['index'].exists() else '❌'}   {C.GRAY}Index des souvenirs ({fact_count} entrées){C.RESET}",
        f"",
        f"  {C.CYAN}Historique{C.RESET}",
        f"    Échanges en mémoire :  {C.YELLOW}{C.BOLD}{len(history)}{C.RESET}",
        f"    Journaux quotidiens :  {C.YELLOW}{C.BOLD}{daily_count}{C.RESET}",
        f"    Journal du jour :      {'✅ ' + today + '.md' if daily_log.exists() else '🆕 pas encore créé'}",
    ]
    print()
    print(draw_box(lines, C.YELLOW))
    print()

def print_thinking():
    print(f"\n{C.CYAN}✦{C.RESET} {C.DIM}Réflexion en cours...{C.RESET}\n")

def print_response(text: str):
    print(f"{C.CYAN}✦{C.RESET} {text}\n")

def print_goodbye():
    print(f"\n{C.PINK}Agent powering down.{C.RESET} {C.GRAY}À bientôt Gauthier !{C.RESET}\n")

# ─── Boucle Principale ────────────────────────────────────────────────

def main():
    os.system("clear" if os.name != "nt" else "cls")
    print_banner()

    while True:
        try:
            user_input = input(f" {C.BLUE}>{C.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print_goodbye()
            break

        if not user_input: continue

        if user_input.lower() in ("/quit", "/exit", "/q", "quit", "exit"):
            print_goodbye()
            break

        if user_input.lower() in ("/status", "status"):
            print_status()
            continue

        if user_input.lower() in ("/clear", "clear"):
            os.system("clear" if os.name != "nt" else "cls")
            print_banner()
            continue

        # Utiliser brain.py pour l'intelligence
        print_thinking()
        response = brain.process_message(user_input)
        print_response(response)

if __name__ == "__main__":
    main()
