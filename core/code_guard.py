#!/usr/bin/env python3
import sys
import os
import shutil
import py_compile
import argparse
from pathlib import Path

def validate_and_install(target_path: str, source_path: str):
    """
    Vérifie la syntaxe d'un fichier Python avant de l'installer à la cible.
    Crée une sauvegarde .bak systématique.
    """
    target = Path(target_path).resolve()
    source = Path(source_path).resolve()
    
    if not source.exists():
        print(f"❌ Erreur : Fichier source introuvable ({source})")
        sys.exit(1)
        
    # 1. Validation de syntaxe
    try:
        py_compile.compile(str(source), doraise=True)
        print(f"✅ Syntaxe Python valide pour {source.name}")
    except py_compile.PyCompileError as e:
        print(f"❌ ERREUR DE SYNTAXE DÉTECTÉE :")
        print("-" * 40)
        print(e.msg)
        print("-" * 40)
        print("\n🚫 Modification annulée pour protéger le système.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue lors de la compilation : {e}")
        sys.exit(1)

    # 2. Sauvegarde (Backup)
    if target.exists():
        bak_path = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, bak_path)
        print(f"📑 Sauvegarde créée : {bak_path.name}")
    
    # 3. Installation atomique
    try:
        # On utilise copy2 + remove au lieu de rename pour éviter les soucis de filesystem
        shutil.copy2(source, target)
        print(f"🚀 Fichier mis à jour avec succès : {target.name}")
        
        # Nettoyage
        if source != target:
            source.unlink()
            
    except Exception as e:
        print(f"❌ Erreur lors de l'installation : {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenBrain Code Gatekeeper — Sécurité d'écriture")
    parser.add_argument("--target", required=True, help="Chemin du fichier final")
    parser.add_argument("--source", required=True, help="Chemin du fichier temporaire à valider")
    
    args = parser.parse_args()
    validate_and_install(args.target, args.source)
