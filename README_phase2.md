\# Personal AI OS — Phase 2: Notes RAG (Retrieval-Augmented Generation)



Adds the ability to ask questions about your own notes. The assistant retrieves the most relevant chunks from your `.txt` files and answers using only that content — grounded in your actual notes, not guesses.



\## How it works



1\. \*\*Chunking\*\* — each `.txt` file in `notes/` is split into overlapping chunks (so context isn't lost at chunk boundaries)

2\. \*\*Embedding\*\* — each chunk is converted into a vector (a list of numbers representing its meaning) using a free local model (`all-MiniLM-L6-v2` via `sentence-transformers`)

3\. \*\*Indexing\*\* — all chunks + their vectors are saved to `notes\_index.json`

4\. \*\*Retrieval\*\* — when you ask a question, it's embedded the same way, then compared against every stored chunk using cosine similarity to find the closest matches

5\. \*\*Generation\*\* — the top matching chunks are inserted into the system prompt as context, and the model is instructed to answer only from that context



This is the same core pattern used by tools like "chat with your PDF" or Notion AI — chunk, embed, retrieve, generate.



\## Setup



```bash

pip install groq python-dotenv sentence-transformers numpy

```



`.env` file (same as Phase 0/1):

```

GROQ\_API\_KEY=your-key-here

```



\## Usage



```bash

mkdir notes

\# add .txt files to the notes/ folder



python rag\_assistant.py --index                  # build/rebuild the index

python rag\_assistant.py --ask-notes "question"    # ask using your notes as context

```



Re-run `--index` any time you add or change a note file.



\## Design notes



\*\*Why local embeddings instead of an API:\*\* keeps this phase fully free and means your notes never leave your machine during indexing — only the final answer-generation step calls an external API (Groq), and only with the small relevant excerpt, not your whole notes folder.



\*\*Why chunks overlap:\*\* if a sentence gets cut exactly at a chunk boundary, overlapping the next chunk by a small amount means that sentence still appears intact in at least one chunk.



\*\*Why the system prompt says "answer ONLY from context":\*\* without this instruction, the model will happily blend its own general knowledge with your notes, making it impossible to tell what came from your data versus what it guessed. Verified by testing: asking about something not in the notes correctly returns "I don't have that information," instead of a fabricated answer.



\*\*Why sources are printed after the answer:\*\* RAG systems should be traceable — showing which file/chunk the answer came from lets you verify the model didn't misread or hallucinate from the retrieved text.



\## What's next



Phase 3 adds real-world actions — connecting to a calendar/task API so the assistant can do things, not just answer questions.

