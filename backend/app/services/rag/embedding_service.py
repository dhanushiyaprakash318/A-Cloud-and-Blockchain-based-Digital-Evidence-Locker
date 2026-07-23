from typing import List

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

MODEL_NAME = "all-MiniLM-L6-v2"

embedding_function = SentenceTransformerEmbeddingFunction(model_name=MODEL_NAME)


def embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts into dense vectors using a local sentence-transformers model."""
    if not texts:
        return []
    return [list(vec) for vec in embedding_function(list(texts))]
