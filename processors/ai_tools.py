from providers.llm_provider import LLMProvider
from processors.retriever import CourseRetriever

class AITools:
    """Module 10: AI Tools"""
    def __init__(self, llm_provider: LLMProvider, retriever: CourseRetriever):
        self.llm = llm_provider.get_llm()
        self.retriever = retriever

    def _query_and_generate(self, course_id: str, search_query: str, prompt_template: str) -> str:
        docs = self.retriever.retrieve_chunks(course_id, search_query, k=3)
        if not docs:
            return "No content found to generate this."
        
        context = "\n".join([doc.page_content for doc in docs])
        prompt = prompt_template.format(context=context)
        
        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            return f"Error: {e}"

    def generate_summary(self, course_id: str) -> str:
        template = """You are an expert educator. Create a professional, well-structured summary of the following course material.

Rules for formatting:
- Use markdown headings (## and ###) for sections
- Use **bold** for key terms and important concepts
- Use bullet points for lists
- Add clear spacing between sections
- Include a brief introduction paragraph
- End with key takeaways

Excerpts:
{context}

Structured Summary:"""
        return self._query_and_generate(course_id, "main concepts overview summary", template)

    def generate_flashcards(self, course_id: str) -> str:
        template = "Create 5 professional educational flashcards based on the following excerpts. Format as Q: [Question] \n A: [Answer]\n\nExcerpts:\n{context}\n\nFlashcards:"
        return self._query_and_generate(course_id, "definitions key terms important facts", template)

    def generate_quiz(self, course_id: str) -> str:
        template = """You are an expert quiz creator. Create a 5-question multiple choice quiz based on the following excerpts.

Rules for formatting:
- Use a markdown heading for the quiz title (e.g., ## Quiz)
- Number each question (e.g., **Question 1:**)
- Format the options as a Markdown bulleted list so they render on separate lines:
  - A) [Option 1]
  - B) [Option 2]
  - C) [Option 3]
  - D) [Option 4]
- Add a blank line between each question
- At the very end, add a section "## Answer Key" with answers listed
- Use markdown formatting throughout

Excerpts:
{context}

Quiz:"""
        return self._query_and_generate(course_id, "important facts core concepts", template)

    def generate_revision_notes(self, course_id: str, topic: str = "") -> str:
        if topic:
            search_query = topic
            topic_str = f" focused specifically on the topic of '{topic}'"
        else:
            search_query = "main concepts overview summary important details"
            topic_str = ""
            
        template = f"Create comprehensive, highly structured revision notes from the following excerpts{{topic_str}}. Use markdown headings, bullet points, and bold text for emphasis. At the very end of your response, you MUST exactly append this text: '\n\n---\n*Generated using LearnLens AI — Created by Om Makwana*'\n\nExcerpts:\n{{context}}\n\nRevision Notes:"
        return self._query_and_generate(course_id, search_query, template)

    def generate_suggested_questions(self, course_id: str) -> list:
        docs = self.retriever.retrieve_chunks(course_id, "main concepts overview summary", k=2)
        if not docs:
            return ["What is this course about?", "What are the key concepts?", "Can you summarize this video?"]
            
        context = "\n".join([doc.page_content for doc in docs])
        prompt = f"""Based on the following transcript excerpts from a course video, generate exactly 3 interesting, specific questions that a student would ask to understand the content better.
        
Excerpts:
{context}

Requirements:
- Output only the 3 questions as a valid JSON list of strings, for example: ["Question 1", "Question 2", "Question 3"]
- Do not add any markdown, numbering, or wrapping text. Just raw JSON list.
- Keep questions short, specific, and direct.

Questions:"""
        try:
            response = self.llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            if raw.startswith("```json"):
                raw = raw.strip("```json").strip("```").strip()
            elif raw.startswith("```"):
                raw = raw.strip("```").strip()
            import json
            questions = json.loads(raw)
            if isinstance(questions, list) and len(questions) > 0:
                return [q.strip() for q in questions[:3]]
        except Exception as e:
            print(f"Error generating suggested questions: {e}")
            
        return ["What is this course about?", "What are the key concepts?", "Can you summarize this video?"]

