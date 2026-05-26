EXTRACT_QUESTIONS_PROMPT = """
You are extracting interview questions from Xiaohongshu posts.

Given a list of candidate lines from a post body, return ONLY the lines that are interview questions.
Interview questions include:
- Technical questions, such as "MySQL 索引原理", "缓存穿透怎么解决", "手撕：LRU"
- Coding tasks, such as "编程题：实现 LRU 缓存", "手撕：数组按 k 分组"
- Scenario/design questions, such as "设计一个短链接系统", "秒杀系统怎么设计"
- Behavioral and project questions, such as "项目怎么上线部署", "介绍你做过的最有挑战的项目"
- Question-like statements, such as "nginx 和 springboot 如何通信", "Redis 为什么快"

NOT interview questions:
- Post titles and metadata, such as "PDD 服务端一面", "2024 校招", "base 上海"
- Sentiment or summary statements, such as "今天面试不太难", "HR 说一周内给结果"
- Single-word topics without context, such as "Redis", "八股"

Return a JSON object with a single field "questions" containing the extracted question lines.
If no questions are found, return {"questions": []}.
"""

CLASSIFY_AND_ENRICH_PROMPT = """
You classify Xiaohongshu interview posts and extract structured information.

Allowed categories: "backend", "ai_agent", "reject".

Reject if the post is primarily about Go, Golang, C++, front-end, PM, or operations.
Only use facts present in the title and extracted question lines.
Never invent company names, rounds, or topics that are not explicitly mentioned.

Return JSON:
{
  "category": "backend" | "ai_agent" | "reject",
  "company_name": "company name or empty string",
  "round_name": "e.g. 一面, 二面, 三面, 终面, HR面, or empty string",
  "normalized_questions": ["question 1", "question 2"],
  "knowledge_tags": ["tag1", "tag2"]
}

When normalizing questions:
- Expand abbreviations, such as db to 数据库 and mq to 消息队列
- Fix obvious typos
- Keep the original meaning intact
- If a question is too vague to understand, mark it "[ambiguous] question text"

Tags should be specific technical topics, such as "MySQL", "Redis", "RAG", "缓存", "分布式", "Spring".
"""

ANSWER_PROMPT = """
You are writing a standard interview answer in Chinese.

Provide an answer that:
- Leads with the key conclusion first in 30-50 Chinese words
- Explains the core principle or approach in 80-150 Chinese words
- Covers practical considerations and trade-offs where relevant
- Ends with a brief summary

The answer should be concise enough to recite in 3-5 minutes in an interview, but detailed enough to demonstrate real understanding.

Return JSON:
{
  "question": "original question",
  "answer": "complete answer in Chinese",
  "why_asked": "what the interviewer is testing with this question",
  "answer_structure": ["step1", "step2", "step3"],
  "follow_ups": ["common follow-up question 1", "follow-up question 2"]
}
"""
