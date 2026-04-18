from pathlib import Path
import os

# Define a raiz do projeto de forma dinâmica
ROOT_DIR = Path(__file__).parent.parent

# Caminhos dos templates de relatório
RELATORIO_TEMPLATE = ROOT_DIR / "templates" / "relatorio" / "index_rel.html"
RELATORIO_CSS = ROOT_DIR / "templates" / "relatorio" / "style_rel.css"

# Caminho da Logo
LOGO_IMG = ROOT_DIR / "gui" / "assets" / "LogoSerrana.jpg"