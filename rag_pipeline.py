import os
import shutil
import logging

import openai
import nltk
import tiktoken

from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from openai import OpenAIError
from chromadb.errors import ChromaError
from dotenv import load_dotenv


load_dotenv()


class RagDatabase:
    """Creates a chroma database from files found in the data folder
    and saves the db to the output path with the provided file name"""

    def __init__(self, data_folder: str, file_name: str, file_type=".md"):

        nltk.download('punkt_tab')
        nltk.download('averaged_perceptron_tagger_eng')

        openai.api_key = os.environ['OPENAI_API_KEY']
        chroma_path_base = os.environ.get('CHROMA_PATH')

        self.CHROMA_PATH = f"{chroma_path_base}/chroma_{file_name}"
        self.DATA_FOLDER = data_folder  # Contains path to the document to be processed for RAG
        self.chunks = None
        self.description = None
        self.file_type = file_type

    def prepare(self):
        self.generate_data_store()

    def generate_data_store(self):
        documents = self.load_documents()
        chunks = self.split_text(documents)
        self.save_to_chroma(chunks)

    def add_manual_description(self, description: str):
        """Set the description for the uploaded document."""
        self.description = description

    def load_documents(self):
        """Loads documents based on the file type (pdf or md), defaults to md"""
        if self.file_type == ".md":
            loader = DirectoryLoader(self.DATA_FOLDER, glob="*.md")
        else:
            loader = DirectoryLoader(self.DATA_FOLDER, glob="*.pdf", loader_cls=PyMuPDFLoader)

        documents = loader.load()

        for doc in documents:
            doc.metadata["description"] = self.description

        return documents

    def split_text(self, documents: list[Document]):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=100,
            length_function=len,
            add_start_index=True,
        )
        self.chunks = text_splitter.split_documents(documents)
        print(f"Split {len(documents)} documents into {len(self.chunks)} chunks.")

        if len(self.chunks) > 10:
            print(self.chunks[10].page_content)
            print(self.chunks[10].metadata)

        document = self.chunks[10]
        print(document.page_content)
        print(document.metadata)

        return self.chunks

    def save_to_chroma(self, chunks: list[Document]):
        max_tokens_per_batch = 5461
        tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")
        embeddings = OpenAIEmbeddings()

        def count_tokens(text):
            return len(tokenizer.encode(text))

        # Clear DB directory first
        if os.path.exists(self.CHROMA_PATH):
            shutil.rmtree(self.CHROMA_PATH)

        # Split into token-safe batches
        batches = []
        current_batch = []
        current_tokens = 0

        for chunk in chunks:
            tokens = count_tokens(chunk.page_content)

            if current_tokens + tokens > max_tokens_per_batch and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(chunk)
            current_tokens += tokens

        if current_batch:
            batches.append(current_batch)

        # First batch creates the DB
        db = Chroma.from_documents(
            documents=batches[0],
            embedding=embeddings,
            persist_directory=self.CHROMA_PATH
        )

        # Subsequent batches (if any)
        for batch in batches[1:]:
            db.add_documents(batch)

        print(f"Saved {len(chunks)} chunks to {self.CHROMA_PATH}.")


class RagQuery:
    """Queries the chroma db for a response to the query text using OpenAI"""

    def __init__(self, document_name: str, number_of_contexts=3):
        self.document_name = document_name
        self.chroma_base = os.environ['CHROMA_PATH']
        self.chroma_path = os.path.join(self.chroma_base, f"chroma_{self.document_name}")

        self.prompt_template = """
        Answer the question based only on the following context:

        {context}

        ---

        Answer the question based on the above context: {question}

        IMPORTANT RULEs: 
        -Use html formatting to display the response on a website, don't use h1 or h2.
        -Don't wrap your answer in brackets or "
        -Your output should only contain the answer and no other internal note or tags
        """

        self.formatted_response = None
        self.number_of_contexts = number_of_contexts

        openai.api_key = os.environ['OPENAI_API_KEY']

    def get_response(self, query_text: str, number_of_contexts: int):
        """Retrieves an AI-generated answer to a given query by performing a similarity search on the document database,
         formatting the context into a prompt, and invoking a language model. It returns the model's response along
         with relevant source metadata and context passages. query_text is the question to be answered and
         number_of_contexts is the number of chunks of text that will be used to answer the question"""
        try:
            embedding_function = OpenAIEmbeddings()
            db = Chroma(persist_directory=self.chroma_path,
                        embedding_function=embedding_function)

            results = db.similarity_search_with_relevance_scores(query_text, k=number_of_contexts)
            if not results or results[0][1] < 0.7:
                # no good match → surface to caller
                raise ValueError("No matching passages exceed relevance threshold.")

            context = "\n\n---\n\n".join(doc.page_content for doc, _ in results)
            prompt = ChatPromptTemplate.from_template(self.prompt_template).format(
                context=context, question=query_text
            )

            # wrap the OpenAI call so, we can catch timeouts, rate limits…
            try:
                model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
                resp = model.invoke(prompt)
            except OpenAIError as oe:
                logging.warning("OpenAI API error: %s", oe)
                raise

            sources = [
                (
                    doc.metadata.get("source", "unknown"),
                    doc.metadata.get("page", "unknown"),
                    doc.metadata.get("start_index"),
                    doc.metadata.get("description", "N/A")
                )
                for doc, _ in results
            ]
            return {
                "response": resp.content,
                "sources": sources,
                "prompt": prompt,
                "context": [doc.page_content for doc, _ in results]
            }

        except ChromaError as ce:
            logging.error("Chroma DB error: %s", ce, exc_info=True)
            raise
        except Exception:
            logging.exception("Unexpected exception in RagQuery.get_response")
            raise

    def get_document_descriptions(self):
        """Searches the Chroma document database for metadata associated with the currently selected document
        (self.document_name) and returns its description. If not found, returns a default fallback message."""
        embedding_function = OpenAIEmbeddings()
        db = Chroma(persist_directory=self.chroma_path, embedding_function=embedding_function)
        print(self.chroma_path)

        # Access all documents
        all_docs = db.get(include=["metadatas"])

        if " " in self.document_name:
            document_name_parts = self.document_name.lower().split(" ")
            for metadata in all_docs["metadatas"]:
                if all(part in metadata.get("source").lower() for part in document_name_parts):
                    print(f"DB with name {self.document_name} found.")
                    description = metadata.get("description", "N/A")
                    return description

                else:
                    description = "Document description not found."
                    return description
        else:
            # Extract descriptions from metadata
            for metadata in all_docs["metadatas"]:
                if self.document_name in metadata.get("source"):
                    print(f"DB with name {self.document_name} found.")
                    description = metadata.get("description", "N/A")
                    return description

                else:
                    description = "Document description not found."
                    return description
