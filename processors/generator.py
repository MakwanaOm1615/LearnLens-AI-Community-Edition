import json
from langchain_core.prompts import PromptTemplate
from providers.llm_provider import LLMProvider
from processors.retriever import CourseRetriever

class AnswerGenerator:
    """Module 7 & Feature 1: Generation & AI Study Mode"""
    def __init__(self, llm_provider: LLMProvider, retriever: CourseRetriever):
        self.llm = llm_provider.get_llm()
        self.retriever = retriever
        self.prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a Professional AI Course Assistant and Tutor. Answer the user's question based ONLY on the provided course transcript excerpts.

Context Excerpts:
{context}

---

User Question: {question}

Instructions:
- Be highly professional, helpful, and clear.
- Base your entire answer strictly on the provided context.
- You MUST output your response in valid JSON format exactly matching the schema below. Do not output markdown code blocks wrapping the JSON, just raw JSON.

JSON Schema required:
{{
  "main_answer": "Your detailed answer here. Cite exact timestamps and titles when stating facts (e.g. 'According to the instructor (01:25)...'). If the answer is not in the context, politely say you don't know.",
  "key_concepts": ["concept1", "concept2"],
  "related_topics": ["topic1", "topic2"],
  "practice_questions": [
    {{"difficulty": "Easy", "question": "..."}},
    {{"difficulty": "Medium", "question": "..."}},
    {{"difficulty": "Hard", "question": "..."}}
  ],
  "learning_tips": "Concise revision advice related to the answer.",
  "confidence_score": 95
}}

Output JSON:"""
        )

    def format_context(self, docs):
        formatted = []
        sources = []
        for doc in docs:
            start_sec = int(doc.metadata["start"])
            mins, secs = divmod(start_sec, 60)
            timestamp = f"{mins:02d}:{secs:02d}"
            formatted.append(f"[{doc.metadata['title']} @ {timestamp}]\n{doc.page_content}")
            sources.append({"title": doc.metadata["title"], "timestamp": timestamp, "seconds": start_sec})
        return "\n\n".join(formatted), sources

    def generate(self, course_id: str, question: str) -> dict:
        docs = self.retriever.retrieve_chunks(course_id, question)
        if not docs:
            return {
                "structured": {
                    "main_answer": "I couldn't find relevant information in the uploaded course videos.",
                    "key_concepts": [],
                    "related_topics": [],
                    "practice_questions": [],
                    "learning_tips": "Upload more videos related to this topic.",
                    "confidence_score": 0
                },
                "sources": []
            }
            
        context_str, sources = self.format_context(docs)
        prompt = self.prompt_template.format(context=context_str, question=question)
        
        try:
            response = self.llm.invoke(prompt)
            raw_text = response.content if hasattr(response, "content") else str(response)
            
            if raw_text.startswith("```json"):
                raw_text = raw_text.strip("```json").strip("```").strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.strip("```").strip()
                
            structured_data = json.loads(raw_text)
            
        except Exception as e:
            import re
            clean_text = raw_text
            
            # Salvage main_answer from broken JSON (even if truncated)
            ans_match = re.search(r'"main_answer"\s*:\s*"(.*?)(?:",|"\s*\}|$)', raw_text, re.IGNORECASE | re.DOTALL)
            if ans_match:
                clean_text = ans_match.group(1).replace('\\n', '\n').replace('\\"', '"')
            else:
                clean_text = clean_text.strip('{').strip('}').strip()

            key_concepts = []
            practice_questions = []
            related_topics = []

            # 1. Extract Key Concepts
            kc_match = re.search(r'\**Key Concepts:\**(.*?)(?=\n\n|\n\**Practice|\n\**Study|\n\**Learning|$)', clean_text, re.IGNORECASE | re.DOTALL)
            if kc_match:
                kc_str = kc_match.group(1).replace('*', '').strip()
                key_concepts = [k.strip() for k in kc_str.split(',') if k.strip()]
                clean_text = clean_text.replace(kc_match.group(0), '')
                
            # 2. Extract Practice Questions
            pq_matches = re.finditer(r'(Easy|Medium|Hard)\s*:\s*(.*?)(?=\n|$)', clean_text, re.IGNORECASE)
            for pq in pq_matches:
                practice_questions.append({"difficulty": pq.group(1).capitalize(), "question": pq.group(2).strip()})
                clean_text = clean_text.replace(pq.group(0), '')
            clean_text = re.sub(r'\**Practice Questions:?\**\s*', '', clean_text, flags=re.IGNORECASE).strip()

            # 3. Extract Study Next / Related Topics
            st_match = re.search(r'\**Study Next:\**(.*?)(?=\n\n|\n\**Practice|\n\**Learning|$)', clean_text, re.IGNORECASE | re.DOTALL)
            if st_match:
                st_str = st_match.group(1).replace('*', '').strip()
                related_topics = [k.strip() for k in st_str.split(',') if k.strip()]
                clean_text = clean_text.replace(st_match.group(0), '')

            structured_data = {
                "main_answer": clean_text.strip(),
                "key_concepts": key_concepts,
                "related_topics": related_topics,
                "practice_questions": practice_questions,
                "learning_tips": "",
                "confidence_score": 0
            }
            
        return {
            "structured": structured_data,
            "sources": sources
        }
