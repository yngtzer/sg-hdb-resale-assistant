import os
from typing import List, Dict
from textwrap import shorten
from openai import OpenAI

def synthesize_answer(query: str, hits: List[Dict]) -> Dict:
    """
    If OPENAI_API_KEY set, ask model to write a concise, stepwise answer using only provided chunks.
    Else, return an extractive bulleted answer.
    """
    citations = [{"title": h["title"], "url": h["url"]} for h in hits[:4]]  # show top 4 sources

    if os.getenv("OPENAI_API_KEY"):
        client = OpenAI()
        context = ""
        for i, h in enumerate(hits, 1):
            context += f"[{i}] {h['title']} | {h['url']}\n{h['text']}\n\n"
        prompt = f"""You are a Singapore HDB resale assistant. Answer the user's question using ONLY the context below.
Be concise, use bullet points or steps, and include short in-text citations like [1], [2] referring to the numbered sources.

Question: {query}

Context:
{context}
"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )
        answer_md = resp.choices[0].message.content
        # Convert [n] to markdown links using our citations
        for i, c in enumerate(citations, 1):
            answer_md = answer_md.replace(f"[{i}]", f"[{i}]({c['url']})")
        return {"answer_markdown": answer_md, "citations": citations}

    # Fallback extractive: show top snippets
    bullets = []
    for i, h in enumerate(hits, 1):
        snippet = shorten(h["text"].replace("\n"," "), width=260, placeholder="…")
        bullets.append(f"- [{i}] [{h['title']}]({h['url']}): {snippet}")
    answer_md = "**Top relevant guidance (extractive fallback):**\n" + "\n".join(bullets)
    return {"answer_markdown": answer_md, "citations": citations}
