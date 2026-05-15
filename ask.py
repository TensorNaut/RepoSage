from rag.pipeline import ask

print("RepoSage — Ask anything about the indexed repository.")
print("Type 'exit' to quit.\n")

while True:
    q = input("You: ").strip()
    if q.lower() == "exit":
        break
    if not q:
        continue
    print("\n" + ask(q) + "\n")