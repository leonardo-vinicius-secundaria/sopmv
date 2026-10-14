from pathlib import Path

text = Path('docs/roteiro_audio_ils.txt').read_text(encoding='utf-8')
lines = [line.strip() for line in text.splitlines() if not line.startswith('.')]
wrapped = []
for line in lines:
    if not line:
        wrapped.append('')
        continue
    while len(line) > 92:
        cut = line.rfind(' ', 0, 92)
        cut = cut if cut > 0 else 92
        wrapped.append(line[:cut])
        line = line[cut:].lstrip()
    wrapped.append(line)

pages = [wrapped[i:i + 48] for i in range(0, len(wrapped), 48)]
objects = []
objects.append('<< /Type /Catalog /Pages 2 0 R >>')
page_ids = []
for page_index, page in enumerate(pages):
    page_ids.append(4 + 2 * page_index)
    content = ['BT', '/F1 10 Tf', '50 770 Td', '13 TL']
    for line in page:
        safe = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        encoded = safe.encode('latin-1', errors='replace').decode('latin-1')
        content.append(f'({encoded}) Tj')
        content.append('0 -13 Td')
    content.append('ET')
    stream = '\n'.join(content).encode('latin-1')
    objects.append(f'<< /Length {len(stream)} >>\nstream\n{stream.decode("latin-1")}\nendstream')
    objects.append('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 ' + str(3 + 2 * len(pages)) + ' 0 R >> >> /Contents ' + str(4 + 2 * page_index) + ' 0 R >>')
objects.insert(1, '<< /Type /Pages /Kids [' + ' '.join(f'{pid} 0 R' for pid in page_ids) + f'] /Count {len(page_ids)} >>')
objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')

pdf = bytearray(b'%PDF-1.4\n')
offsets = [0]
for number, obj in enumerate(objects, 1):
    offsets.append(len(pdf))
    pdf.extend(f'{number} 0 obj\n'.encode())
    pdf.extend(obj.encode('latin-1'))
    pdf.extend(b'\nendobj\n')
xref = len(pdf)
pdf.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
for offset in offsets[1:]:
    pdf.extend(f'{offset:010d} 00000 n \n'.encode())
pdf.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
Path('docs/roteiro_audio_ils.pdf').write_bytes(pdf)
