"""Vérifie que le serveur MCP expose bien les outils (nécessite `mcp<2`)."""

import asyncio
import sys
import unittest
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:  # pragma: no cover
    ClientSession = None

SERVER = Path(__file__).resolve().parent.parent / "mcp_server.py"


async def _run():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            cal = await session.call_tool("get_calendrier",
                                          {"module": "Réseaux"})
            dem = await session.call_tool("generer_demande", {
                "nom_etudiant": "Sami Test", "numero_etudiant": "ET12345",
                "module": "Réseaux", "motif": "maladie"})
            return names, cal.content[0].text, dem.content[0].text


@unittest.skipIf(ClientSession is None, "paquet mcp non installé")
class TestMcp(unittest.TestCase):

    def test_outils_exposes_et_executes(self):
        names, cal, dem = asyncio.run(_run())
        self.assertEqual(
            names, {"search_reglement", "get_calendrier", "generer_demande"})
        self.assertIn("18/01/2027", cal)
        self.assertIn("NON ENVOYÉ", dem)       # brouillon, jamais d'envoi
        self.assertNotIn("envoyer_demande", names)


if __name__ == "__main__":
    unittest.main()
