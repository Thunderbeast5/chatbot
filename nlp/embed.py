from sentence_transformers import SentenceTransformer
import numpy as np
import pickle
import os

# Load model (lightweight)
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_text(text):
    """Generate embedding for a single text"""
    return model.encode(text)

def embed_texts(texts):
    """Generate embeddings for multiple texts"""
    return model.encode(texts)

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def semantic_search(query, documents, top_k=5):
    """
    Perform semantic search on documents
    Returns top_k most similar documents
    """
    query_embedding = embed_text(query)
    doc_embeddings = embed_texts(documents)
    
    similarities = []
    for i, doc_emb in enumerate(doc_embeddings):
        sim = cosine_similarity(query_embedding, doc_emb)
        similarities.append((i, sim))
    
    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    return similarities[:top_k]

class IdeaSearchEngine:
    """Search engine for business ideas"""
    
    def __init__(self):
        self.ideas = []
        self.embeddings = None
        self.cache_file = 'data/idea_embeddings.pkl'
    
    def load_ideas(self, ideas):
        """Load ideas and generate embeddings"""
        self.ideas = ideas
        
        # Check if cached embeddings exist
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.embeddings = pickle.load(f)
                print("Loaded cached embeddings")
                return
            except:
                pass
        
        # Generate embeddings
        descriptions = [f"{idea['title']} {idea['description']} {idea.get('tags', '')}" 
                       for idea in ideas]
        self.embeddings = embed_texts(descriptions)
        
        # Cache embeddings
        os.makedirs('data', exist_ok=True)
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.embeddings, f)
        print("Generated and cached embeddings")
    
    def search(self, query, filters=None, top_k=5):
        """
        Search for ideas based on query
        filters: dict with keys like 'category', 'budget_max', etc.
        """
        if not self.ideas or self.embeddings is None:
            return []
        
        query_embedding = embed_text(query)
        
        # Calculate similarities
        results = []
        for i, idea_emb in enumerate(self.embeddings):
            idea = self.ideas[i]
            
            # Apply filters
            if filters:
                if 'category' in filters and filters['category']:
                    if filters['category'] not in idea.get('categories', ''):
                        continue
                
                if 'budget_max' in filters and filters['budget_max']:
                    if idea.get('required_investment_min', 0) > filters['budget_max']:
                        continue
            
            sim = cosine_similarity(query_embedding, idea_emb)
            results.append({
                'idea': idea,
                'similarity': float(sim)
            })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:top_k]

# Global search engine instance
search_engine = IdeaSearchEngine()
