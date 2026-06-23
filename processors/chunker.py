from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from models.data_models import Transcript

class TranscriptChunker:
    """Module 3: Chunking"""
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 300):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""]
        )

    def chunk_transcript(self, transcript: Transcript) -> list[Document]:
        """
        Uses Langchain's RecursiveCharacterTextSplitter on the full text,
        then carefully maps the resulting chunks back to their exact timestamps.
        """
        full_text = transcript.full_text
        
        # Build an index mapping char position to timestamp
        char_to_time = []
        current_idx = 0
        
        for c in transcript.chunks:
            text_len = len(c.text)
            char_to_time.append({
                "start_idx": current_idx,
                "end_idx": current_idx + text_len,
                "start_time": c.start,
                "end_time": c.end,
                "title": c.title
            })
            current_idx += text_len + 1 # +1 for the space joined in full_text
            
        # Split the text
        split_texts = self.splitter.split_text(full_text)
        
        documents = []
        search_start = 0
        
        for text in split_texts:
            # Find the exact character position of this split chunk
            start_pos = full_text.find(text, search_start)
            if start_pos == -1:
                start_pos = search_start # Fallback
                
            end_pos = start_pos + len(text)
            
            # Advance the search_start pointer slightly before the end to allow for overlap
            search_start = start_pos + max(1, len(text) - self.chunk_overlap)
            
            start_time = 0.0
            end_time = 0.0
            title = transcript.chunks[0].title if transcript.chunks else "Unknown"
            
            # Find the whisper chunk that contains the start_pos
            for mapping in char_to_time:
                if mapping["start_idx"] <= start_pos <= mapping["end_idx"]:
                    start_time = mapping["start_time"]
                    title = mapping["title"]
                    break
                    
            # Find the whisper chunk that contains the end_pos
            for mapping in reversed(char_to_time):
                if mapping["start_idx"] <= end_pos <= mapping["end_idx"]:
                    end_time = mapping["end_time"]
                    break
                    
            # If end_time is still 0 (e.g. edge case), grab the last available time
            if end_time == 0.0 and char_to_time:
                end_time = char_to_time[-1]["end_time"]
                    
            doc = Document(
                page_content=text,
                metadata={
                    "start": start_time,
                    "end": end_time,
                    "title": title
                }
            )
            documents.append(doc)
            
        return documents
