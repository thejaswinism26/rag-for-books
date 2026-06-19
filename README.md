📚 SecondMind – AI-Powered Personal Knowledge Library

An AI-powered RAG system that transforms your personal book collection into a searchable second brain. Upload books, generate summaries, and ask natural language questions with answers grounded in the books you've read.

🌟 Overview

SecondMind is a Retrieval-Augmented Generation (RAG) application that helps you retain and interact with the knowledge from your personal library. Instead of manually searching through books or trying to remember where you read something, SecondMind indexes your collection and lets you query it conversationally.

The system retrieves relevant passages from your books and uses a reranking model to identify the most useful context before passing it to a Large Language Model (LLM). This results in more accurate, relevant, and context-aware answers while reducing irrelevant retrievals.

Whether you're studying, researching, or revisiting old books, SecondMind acts as a persistent AI assistant built around your own reading history.

✨ Features
📖 Upload and organize your personal book library
🤖 RAG-based question answering
📝 AI-generated book summaries
🔍 Semantic document retrieval
🎯 Cross-encoder reranking for improved retrieval accuracy
💬 Natural language conversations with your books
🧠 Persistent knowledge base that grows with every book
📚 Search across multiple books simultaneously
⚡ Fast and context-aware responses grounded in source material
🏗️ System Architecture
               User Question
                     │
                     ▼
          Semantic Vector Retrieval
                     │
                     ▼
        Retrieve Top-K Candidate Chunks
                     │
                     ▼
           Cross-Encoder Reranker
                     │
                     ▼
         Select Most Relevant Chunks
                     │
                     ▼
              Large Language Model
                     │
                     ▼
        Grounded Answer / Summary
🧠 Retrieval Pipeline

Unlike a basic RAG system that directly feeds retrieved documents to an LLM, SecondMind includes a reranking stage.

1. Semantic Retrieval

The query is converted into an embedding and compared against embeddings of book passages stored in the vector database.

This retrieves the Top-K candidate chunks that are semantically similar to the user's question.

2. Reranking

The retrieved candidates are passed through a cross-encoder reranking model.

Instead of comparing embeddings independently, the reranker evaluates the query and each candidate passage together, assigning a relevance score to each.

The highest-scoring passages are selected as the final context for the LLM.

Benefits include:

Higher retrieval precision
Better contextual relevance
Fewer irrelevant chunks
More accurate grounded responses
3. Answer Generation

The selected passages are provided to the LLM, which generates a response based only on the retrieved context, helping reduce hallucinations and improve factual consistency.
