"""Generates docs/architecture.png  (run: python docs/generate_architecture.py)"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")


def box(x, y, w, h, text, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15",
                                fc=color, ec="#333", lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10, weight="bold")


def arrow(a, b, both=False):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="<->" if both else "->", lw=1.6, color="#444"))


ax.text(8, 8.6, "Career Copilot - System Architecture", ha="center", fontsize=16, weight="bold")

box(0.3, 6.8, 1.8, 1.0, "User", "#FDE68A")
box(3.0, 6.8, 3.0, 1.0, "Streamlit UI\nChat | Docs | ATS | Tracker", "#BFDBFE")
box(6.4, 6.4, 4.4, 1.6, "AGENT LOOP\nUnderstand > Decide > Tool > Respond\n+ Prompt layer (modes, few-shot)", "#C7D2FE")
box(11.6, 6.9, 3.9, 1.0, "Groq LLM API\nopenai/gpt-oss-120b", "#FBCFE8")

box(6.4, 3.5, 4.4, 2.1, "TOOLS\nsearch_documents | ats_keyword_match\nadd/list/update/delete_job\ncompany_lookup | get_current_time", "#BBF7D0")
box(11.6, 4.7, 3.0, 0.9, "SQLite Job Tracker", "#E9D5FF")
box(11.6, 3.5, 3.0, 0.9, "Wikipedia API", "#E9D5FF")

ax.text(0.3, 2.35, "RAG ingestion pipeline", fontsize=11, weight="bold", color="#065F46")
box(0.3, 0.7, 1.9, 1.1, "Upload\nPDF/DOCX/TXT", "#FEF3C7")
box(2.7, 0.7, 1.9, 1.1, "Loader", "#FEF3C7")
box(5.1, 0.7, 1.9, 1.1, "Chunker\n(overlap)", "#FEF3C7")
box(7.5, 0.7, 2.3, 1.1, "Embeddings\nMiniLM-L6-v2", "#FEF3C7")
box(10.3, 0.7, 2.3, 1.1, "ChromaDB\nVector Store", "#FDBA74")

arrow((2.1, 7.3), (3.0, 7.3))
arrow((6.0, 7.3), (6.4, 7.3))
arrow((10.8, 7.45), (11.6, 7.45), both=True)
arrow((8.6, 6.4), (8.6, 5.6))
arrow((10.8, 5.0), (11.6, 5.15))
arrow((10.8, 4.2), (11.6, 3.95))
arrow((4.0, 6.8), (1.4, 1.8))
for a, b in [(2.2, 2.7), (4.6, 5.1), (7.0, 7.5), (9.8, 10.3)]:
    arrow((a, 1.25), (b, 1.25))
arrow((11.4, 1.8), (9.2, 3.5), both=True)
ax.text(11.0, 2.55, "semantic search", fontsize=9, style="italic", color="#92400E")

plt.savefig("docs/architecture.png", dpi=130, bbox_inches="tight", facecolor="white")
print("saved")
