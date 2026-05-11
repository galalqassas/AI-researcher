BUCKET_SUMMARY = """You are a research analyst. Given a list of academic papers in the "{bucket}" research domain, write a concise plain-English summary (about 500 words) of the key themes, findings, and trends.

Papers:
{papers}

Write the summary in clear, non-technical language that a business team can understand. Focus on:
1. Key themes across the papers
2. Most important findings
3. Practical implications
"""

CROSS_BUCKET_SYNTHESIS = """You are a research analyst. Given summaries of research papers from three domains — General AI, Autonomous Agents, and AI+Finance — write a brief synthesis (about 300 words) highlighting:
1. Overlapping themes across domains
2. Emerging trends worth watching
3. Strategic implications for a financial services company

General AI Summary:
{general_ai}

Autonomous Agents Summary:
{autonomous_agents}

AI+Finance Summary:
{ai_finance}
"""

PER_PAPER_SUMMARY = """In 1-2 sentences, summarize the key contribution of this paper:

Title: {title}
Abstract: {abstract}
"""