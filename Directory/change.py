from pypdf import PdfReader, PdfWriter

# Load your current resume PDF with the cross-reference stream
reader = PdfReader("../resume_remaining.pdf")
writer = PdfWriter()

# Copy all pages into the writer object
for page in reader.pages:
    writer.add_page(page)

# Writing it out forces pypdf to reconstruct a traditional xref table + trailer
output_filename = "../remaining_traditional.pdf"
with open(output_filename, "wb") as out_file:
    writer.write(out_file)

print(f"Success! Converted file saved as: {output_filename}")
