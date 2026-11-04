"""Rule-based ATS keyword matching (pure Python, no API calls)."""
import re
from collections import Counter

STOP = set("""a an the and or but if then of to in on at by for with from as is are was were be been being this that
these those it its we you your our they their he she his her i me my not no yes can will would should could may
might must shall do does did done have has had having about into over under per via etc such than also more most
other any all each both few some many much very well new use used using work working works team teams ability
able strong skills skill years year role job company required preferred including include includes responsibilities
requirements requirement looking build building maintain develop developing good great knowledge experience familiarity
junior senior engineer developer nice plus candidate candidates responsible across within who what when where how while out up""".split())

KNOWN_SKILLS = [
    "python", "sql", "java", "javascript", "typescript", "c++", "pandas", "numpy", "scikit-learn", "tensorflow",
    "pytorch", "streamlit", "fastapi", "flask", "django", "docker", "kubernetes", "git", "github", "aws", "azure",
    "gcp", "linux", "ci/cd", "rest api", "langchain", "llamaindex", "chromadb", "pinecone", "faiss", "rag",
    "prompt engineering", "machine learning", "deep learning", "nlp", "embeddings", "vector database",
    "tool calling", "function calling", "power bi", "tableau", "excel", "react", "node.js", "mongodb",
    "postgresql", "mysql", "data analysis", "llm", "openai", "groq", "agents",
]


def tokenize(text: str) -> list[str]:
    return [t.rstrip(".-") for t in re.findall(r"[a-z][a-z0-9+#./\-]*", text.lower()) if len(t.rstrip(".-")) > 1]


def _has(term: str, low: str) -> bool:
    base = term[:-1] if term.endswith("s") and len(term) > 3 else term  # tolerate plurals
    return re.search(rf"(?<![a-z0-9]){re.escape(base)}s?(?![a-z0-9])", low) is not None


def extract_keywords(jd: str, top_n: int = 25) -> list[str]:
    low = jd.lower()
    counts = Counter(t for t in tokenize(jd) if t not in STOP and len(t) > 2)
    for skill in KNOWN_SKILLS:
        if _has(skill, low):
            counts[skill] += 5  # boost recognised skills
    covered = {w for k in counts if " " in k for w in k.split()}
    ranked = [k for k, _ in counts.most_common() if " " in k or k not in covered]
    return ranked[:top_n]


def ats_match(jd: str, resume: str, top_n: int = 25) -> dict:
    keywords = extract_keywords(jd, top_n)
    low = resume.lower()
    matched = [k for k in keywords if _has(k, low)]
    missing = [k for k in keywords if k not in matched]
    score = round(100 * len(matched) / len(keywords)) if keywords else 0
    return {"score": score, "matched": matched, "missing": missing, "total": len(keywords)}
