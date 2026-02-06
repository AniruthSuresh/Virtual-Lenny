# Virtual Lenny
>  Retrieval-Augmented Generation (RAG) system that recreates **Lenny Rachitsky’s product thinking style** using AWS serverless infrastructure, vector search, and real-time WebSocket streaming.

This project builds a **full end-to-end RAG pipeline**  from scraping real PM content to serving low-latency, streaming answers in a  web UI.

**Target persona**:  [Lenny Rachitsky on LinkedIn](https://www.linkedin.com/in/lennyrachitsky/)


---

## Demo

![Virtual Lenny Demo](./results/virtual-lenny-demo.gif)

**Live demo**:  
🌐 https://virutal-lenny-with-eval.vercel.app/

For testing and evaluation, I also included a small script at `src/generate-synthetic-questions.py`.

This script generates a set of synthetic questions derived from both **LinkedIn posts** and **YouTube transcripts**, and can be used to test the RAG pipeline . 



> NOTE : The first response might take around **7 -12** seconds because I’m using a **mxbai-embed-large-v1** for better retrieval quality (see ablation run time and accuracy across models below). Loading it adds some latency, but the quality boost was worth it for now. Optimizing this tradeoff is an active direction I plan to explore.

![Ablation on time](./results/mixed_embeddings_combined_vertical.png)




## High-Level Architecture

> A detailed, component-by-component breakdown is available in `implementation.md`.  
> This section gives a high-level view of how the system fits together.

### 1. Data Ingestion

Content is ingested from **LinkedIn posts** (via **Apify**) and **YouTube transcripts**, orchestrated end-to-end using **AWS Step Functions** (`/infra/stacks/ingestion_stack.py`). The pipeline follows a structured flow — *Scrape → Clean → Chunk → Embed → Store* — with smart chunking strategies: LinkedIn posts are stored as full, self-contained documents, while YouTube transcripts are split into ~2000-character overlapping segments for better semantic recall. All embeddings are persisted in **Qdrant Cloud**, provisioned via `/infra/stacks/storage_stack.py`.

The deployment success for both the stacks on aws step function : 

![deployment success](./results/ingestion-storage-stack-results.png)

---

### 2. RAG Agent

The RAG agent embeds user queries using `mixedbread-ai/mxbai-embed-large-v1` (1024 dimensions) and performs semantic retrieval against **Qdrant Cloud** to fetch the most relevant context. Responses are generated via **AWS Bedrock (Nova Lite)** with token-level streaming and delivered to the client in real time over a **WebSocket API**.

Each response is automatically evaluated using an internal **RAG quality scorer**, which measures retrieval relevance, groundedness , coherence and retrieved context(youtube / linkedin in this case). 

---

### 3. Web Interface

The **frontend** is built using **Next.js 15** and **React 19**, with a simple terminal-style UI using **Tailwind CSS**. I’m still relatively new to frontend work, so this part of the project focuses more on getting the system working end-to-end rather than visual polish, and there may be a few rough edges. The client talks to the backend over a persistent WebSocket connection, streams tokens in real time, and shows the RAG quality score alongside each response. The frontend is deployed on **Vercel**.


The **backend** exposes a **WebSocket API Gateway** (`/infra/stacks/websocket_stack.py`) backed by **AWS Lambda**, responsible for managing connections, routing messages to the RAG agent, and streaming partial responses back to the client. This setup enables real-time interaction and cleanly separates connection lifecycle management (connect / disconnect) from message handling and model inference, which lives under `/agent/*`.


## Setup 

### 1️⃣ Conda Environment (for local testing)

```bash
conda create -n virtual-lenny python=3.11 -y
conda activate virtual-lenny
```


