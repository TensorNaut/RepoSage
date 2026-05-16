# test_files.py
from ingestion.vector_store import list_indexed_files, query_by_file

files = list_indexed_files("code")
print(f"Total indexed files: {len(files)}")
for f in files:
    print(f"  {f}")

# Test the fix directly
print("\n--- Testing query_by_file('app.py') ---")
results = query_by_file("app.py")
print(f"Chunks found: {len(results)}")
for r in results[:2]:
    print(f"\n[{r['metadata']['path']}]")
    print(r["text"][:200])

print("\n--- Testing query_by_file('generator.py') ---")
results = query_by_file("generator.py")
print(f"Chunks found: {len(results)}")
for r in results[:2]:
    print(f"\n[{r['metadata']['path']}]")
    print(r["text"][:200])