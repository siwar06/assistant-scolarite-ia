"""Démonstration du serveur MCP avec un vrai client MCP (sans Node.js).

    python demo_mcp.py

Lance mcp_server.py, se connecte par le protocole MCP (stdio), liste les
outils exposés puis en exécute deux. Sert de capture pour le rapport (à la
place de MCP Inspector) et de démonstration en soutenance.
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "mcp_server.py"
LINE = "─" * 72


def first_line(text):
    return " ".join((text or "").split())[:110]


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    # Les journaux du serveur (stderr) sont masqués pour une sortie propre.
    async with stdio_client(params, errlog=open(os.devnull, "w")) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(LINE)
            print(f"Serveur MCP : {info.serverInfo.name}   "
                  f"(protocole {info.protocolVersion})")
            print(LINE)

            tools = (await session.list_tools()).tools
            print(f"{len(tools)} outils exposés :\n")
            for t in tools:
                args = ", ".join(t.inputSchema.get("properties", {}))
                print(f"  • {t.name}({args})")
                print(f"      {first_line(t.description)}…")

            names = {t.name for t in tools}
            print(f"\nOutil d'envoi exposé ? "
                  f"{'OUI (problème)' if 'envoyer_demande' in names else 'NON : aucun outil ne peut envoyer'}")

            print("\n" + LINE)
            print("Appel : get_calendrier(module='Réseaux')")
            print(LINE)
            cal = await session.call_tool("get_calendrier",
                                          {"module": "Réseaux"})
            print(cal.content[0].text)

            print("\n" + LINE)
            print("Appel : generer_demande(Sami Test, ET12345, Réseaux, maladie)")
            print(LINE)
            dem = await session.call_tool("generer_demande", {
                "nom_etudiant": "Sami Test", "numero_etudiant": "ET12345",
                "module": "Réseaux", "motif": "maladie"})
            print(dem.content[0].text.splitlines()[0])
            print("…\n(le brouillon n'est jamais envoyé : l'étudiant doit "
                  "confirmer dans l'interface)")


if __name__ == "__main__":
    asyncio.run(main())
