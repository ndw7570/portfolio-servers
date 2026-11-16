import zipfile, xml.etree.ElementTree as ET
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
def col_idx(ref):
    n = 0
    for ch in ref:
        if ch.isalpha(): n = n * 26 + ord(ch.upper()) - 64
    return n - 1
def sheets(p):
    z = zipfile.ZipFile(p); ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(M + 'si'):
            ss.append(''.join(t.text or '' for t in si.iter(M + 't')))
    rmap = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    out = {}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find(M + 'sheets'):
        tgt = rmap[s.get(R)].lstrip('/'); tgt = tgt if tgt.startswith('xl/') else 'xl/' + tgt
        rows = []
        for r in ET.fromstring(z.read(tgt)).iter(M + 'row'):
            vals = []
            for c in r.findall(M + 'c'):
                i = col_idx(c.get('r')); v = c.find(M + 'v'); t = c.get('t')
                while len(vals) < i: vals.append('')
                if t == 's' and v is not None: vals.append(ss[int(v.text)])
                elif t == 'inlineStr': vals.append(''.join(x.text or '' for x in c.iter(M + 't')))
                else: vals.append(v.text if v is not None else '')
            rows.append(vals)
        out[s.get('name')] = rows
    return out
