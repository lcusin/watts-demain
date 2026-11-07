"""Ecrire un court bilan ; les explications detaillees sont dans docs/."""


def ecrire_resume(dossier, titre, explication, tableau=None):
    texte = f"# {titre}\n\n{explication}\n"
    if tableau is not None:
        texte += "\n```text\n" + tableau.round(3).to_string(index=False) + "\n```\n"
    (dossier / "RESULTATS.md").write_text(texte, encoding="utf-8")
