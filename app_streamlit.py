"""Interface Streamlit – Assistant de scolarité ISET Charguia.

Lancement :  streamlit run app_streamlit.py

Streamlit est le point d'entrée : il démarre en arrière-plan le serveur
FastAPI du projet (server.py : agent, validation humaine, API) puis affiche
l'interface web web/index.html dans la page. Une seule commande suffit.
La version 100 % Streamlit native est dans app_streamlit_native.py.
"""

import socket
import sys
import threading
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

HOST, PORT = "127.0.0.1", 8000
URL = f"http://{HOST}:{PORT}"

st.set_page_config(page_title="Assistant de scolarité – ISET Charguia",
                   page_icon="🎓", layout="wide",
                   initial_sidebar_state="collapsed")


def _port_open():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, PORT)) == 0


@st.cache_resource
def start_backend():
    """Démarre FastAPI une seule fois (Streamlit relance le script à chaque
    interaction). Si server.py tourne déjà sur le port 8000, on le réutilise."""
    if _port_open():
        return "existant"

    import uvicorn
    import server  # server.py : app FastAPI + agent + validation humaine

    config = uvicorn.Config(server.app, host=HOST, port=PORT,
                            log_level="warning")
    threading.Thread(target=uvicorn.Server(config).run, daemon=True).start()

    for _ in range(50):  # attend jusqu'à ~10 s
        if _port_open():
            return "démarré"
        time.sleep(0.2)
    return "échec"


status = start_backend()

# Page pleine largeur, sans marges Streamlit autour de l'interface.
st.markdown("""
<style>
header[data-testid="stHeader"], footer { display: none; }
.block-container { padding: 0 !important; max-width: 100% !important; }
.stApp { background: #EDEEF6; }
html, body, .stApp, [data-testid="stAppViewContainer"], section.main, [data-testid="stMain"] { overflow: hidden !important; height: 100vh; }
[data-testid="stMainBlockContainer"], [data-testid="stVerticalBlock"] { gap: 0 !important; }
iframe { border: 0; width: 100%; height: 100vh !important; display: block; }
</style>
""", unsafe_allow_html=True)

if status == "échec":
    st.error("Le serveur FastAPI n'a pas démarré. Lancez `python server.py` "
             "dans un terminal puis rechargez la page.")
else:
    components.iframe(URL, height=900, scrolling=False)