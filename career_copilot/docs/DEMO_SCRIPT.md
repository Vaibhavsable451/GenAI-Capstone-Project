# 3-4 minute demo video script

Record with any screen recorder (Windows: Win+G, or OBS / Loom). Speak calmly, one feature at a time.

| Time | Show | Say |
|---|---|---|
| 0:00 | Title / app home | "This is Career Copilot, a GenAI app that combines LLM APIs, prompt engineering, RAG, tools and an agent." |
| 0:20 | Architecture diagram (About tab) | "Documents go through chunking and embeddings into ChromaDB. The agent uses Groq gpt-oss-120b and decides when to call tools." |
| 0:50 | Documents tab: load sample data | "I load a resume and a job description; they are chunked and embedded locally." |
| 1:20 | Copilot, Resume Reviewer mode: "Review my resume against the Junior AI Engineer JD" | "Watch the agent steps: it searches my documents, runs the ATS match tool, then answers using only my real experience." |
| 2:00 | ATS Match tab | "Rule-based keyword score plus a structured JSON analysis from the LLM: strengths, gaps, bullet suggestions." |
| 2:30 | Chat: "Add Google - ML Intern to my tracker as Applied" then open Job Tracker tab | "The agent writes to a SQLite database through a tool." |
| 3:00 | Try "Delete job 1" with destructive toggle off | "Safety guard: destructive actions are blocked unless I enable them." |
| 3:20 | Switch to Interview Coach mode | "Few-shot prompting gives STAR-style feedback on my answers." |
| 3:40 | GitHub repo + live URL | "Code, docs, tests and deployment are all in the repository. Thanks for watching." |
