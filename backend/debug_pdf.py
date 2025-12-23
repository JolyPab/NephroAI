"""Debug script to see extracted text from PDF."""
import fitz
import sys

if __name__ == "__main__":
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "../013231840002.pdf"
    
    doc = fitz.open(pdf_path)
    text_parts = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        text_parts.append(f"=== Page {page_num + 1} ===\n{page_text}")
    
    full_text = "\n".join(text_parts)
    
    # Save to file
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(full_text)
    
    print(f"Text extracted from {len(doc)} pages, saved to extracted_text.txt")
    print(f"Total length: {len(full_text)} characters")
    doc.close()

