import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from commons.logger import logger
from dotenv import load_dotenv

load_dotenv()

log = logger(__name__)

# Constants
CHROMA_PERSIST_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma"
)


class KnowledgeBase:
    def __init__(self):
        # Initialize HuggingFace Embeddings (works locally, no API needed)
        log.info("Initializing HuggingFace embeddings...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        # Initialize ChromaDB Vector Store (local, persistent)
        try:
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            self.vector_store = Chroma(
                persist_directory=CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings,
                collection_name="loan_documents",
            )
            log.info(f"Connected to ChromaDB at {CHROMA_PERSIST_DIR}")
        except Exception as e:
            log.error(f"Failed to initialize ChromaDB: {e}")
            raise e

        # Check for LlamaParse API key
        self.llamaparse_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if self.llamaparse_api_key:
            log.info("LlamaParse API key found - will use for advanced PDF parsing")
        else:
            log.info("LlamaParse API key not found - using standard PyPDF loader")

    def add_document(self, file_path: str):
        """
        Process and add a document (PDF or Text) to ChromaDB.
        """
        try:
            log.info(f"Processing document: {file_path}")

            if file_path.endswith(".pdf"):
                # Try LlamaParse if API key is available
                if self.llamaparse_api_key:
                    try:
                        log.info("Attempting LlamaParse PDF extraction...")
                        from llama_parse import LlamaParse

                        parser = LlamaParse(
                            api_key=self.llamaparse_api_key,
                            result_type="markdown",
                            verbose=False,
                        )

                        # LlamaParse returns a list of document objects
                        parsed_docs = parser.load_data(file_path)

                        # Convert to LangChain Document format
                        from langchain.schema import Document

                        langchain_docs = [
                            Document(
                                page_content=doc.text,
                                metadata={
                                    "source": file_path,
                                    "page": i,
                                    "parser": "llamaparse",
                                },
                            )
                            for i, doc in enumerate(parsed_docs)
                        ]
                        log.info(
                            f"LlamaParse successfully extracted {len(langchain_docs)} pages"
                        )
                    except Exception as e:
                        log.warning(f"LlamaParse failed: {e}, falling back to PyPDF")
                        loader = PyPDFLoader(file_path)
                        langchain_docs = loader.load()
                        for doc in langchain_docs:
                            doc.metadata["parser"] = "pypdf"
                else:
                    # Use standard PyPDF loader
                    log.info("Using PyPDF for PDF extraction...")
                    loader = PyPDFLoader(file_path)
                    langchain_docs = loader.load()
                    for doc in langchain_docs:
                        doc.metadata["parser"] = "pypdf"
            else:
                # Text file
                loader = TextLoader(file_path)
                langchain_docs = loader.load()

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
            chunks = text_splitter.split_documents(langchain_docs)

            log.info(f"Split document into {len(chunks)} chunks")

            # Add to vector store
            self.vector_store.add_documents(chunks)

            log.info("Document successfully added to Knowledge Base")
            return len(chunks)
        except Exception as e:
            log.error(f"Failed to add document: {e}")
            raise e

    def query(self, query_text: str, k: int = 3) -> str:
        """
        Retrieve relevant context for a query.
        """
        try:
            log.info(f"Querying Knowledge Base: {query_text}")

            # Perform similarity search
            results = self.vector_store.similarity_search(query_text, k=k)

            if not results:
                return "No relevant information found in the knowledge base."

            context = "\n\n".join([doc.page_content for doc in results])
            return context
        except Exception as e:
            log.error(f"Failed to query knowledge base: {e}")
            return "Error retrieving information from database."

    def clear(self):
        """
        Clear the knowledge base (delete all documents).
        Warning: This deletes everything in the collection.
        """
        try:
            # Delete and recreate the collection
            self.vector_store.delete_collection()
            self.vector_store = Chroma(
                persist_directory=CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings,
                collection_name="loan_documents",
            )
            log.info("Knowledge Base cleared (All documents deleted)")
        except Exception as e:
            log.error(f"Failed to clear knowledge base: {e}")


# Global instance
kb = KnowledgeBase()
