"""Serveur MCP de l'assistant de scolarité (ISET Charguia).

Expose les outils de src/tools.py à n'importe quel client MCP
(Claude Desktop, MCP Inspector, ou l'agent du projet).

Lancement :   python mcp_server.py          (transport stdio)
Inspection :  npx @modelcontextprotocol/inspector python mcp_server.py

Sécurité : aucun outil n'envoie de message. generer_demande ne crée qu'un
BROUILLON ; l'envoi exige la confirmation de l'étudiant dans l'interface.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mcp.server.fastmcp import FastMCP

import tools

mcp = FastMCP("scolarite-iset-charguia")


@mcp.tool()
def search_reglement(query: str) -> str:
    """Recherche des extraits dans le règlement des études et le calendrier
    des examens de l'ISET Charguia. À utiliser avant de répondre à une
    question sur les absences, justificatifs, rattrapages, stages ou
    réclamations. Les articles sont cités dans les extraits."""

    return tools.search_reglement(query)


@mcp.tool()
def get_calendrier(module: str) -> str:
    """Date, heure et salle de l'examen et du rattrapage d'un module
    (ex. « Bases de données », « Réseaux »). Ne devine jamais une date."""

    return tools.get_calendrier(module)


@mcp.tool()
def generer_demande(
    nom_etudiant: str,
    numero_etudiant: str,
    module: str,
    motif: str,
) -> str:
    """Prépare le BROUILLON d'une demande de rattrapage (Articles 7 et 8).
    motif : « maladie » ou « hospitalisation ». N'envoie rien : l'étudiant
    doit relire puis confirmer l'envoi lui-même. Ne jamais inventer le nom
    ou le numéro étudiant : les demander à l'étudiant."""

    return tools.generer_demande(
        nom_etudiant, numero_etudiant, module, motif
    )


if __name__ == "__main__":
    mcp.run()
