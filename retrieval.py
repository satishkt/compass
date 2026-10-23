"""Deterministic lexical passage retrieval for the first cut; AI Search is a later adapter."""
import math
import re
from collections import Counter
from pathlib import Path

STOP = set('the a an and or to of in is are how what which for on it this that with be do does can i we you our from as by at about'.split())
def tokens(s):
    return [x for x in re.findall(r'[a-z0-9_]+', s.lower()) if x not in STOP and len(x) > 1]

class Index:
    def __init__(self, root):
        self.passages = []
        for f in sorted(Path(root).glob('*.md')):
            body = f.read_text()
            for i, section in enumerate(re.split(r'(?m)(?=^## )', body)):
                # Bound retrieval context, retaining paragraph boundaries and file provenance.
                paragraphs = section.split('\n\n')
                chunk = ''
                part = 0
                for para in paragraphs:
                    if len(chunk) + len(para) > 2600 and chunk:
                        self.add(f.name, f'{i}.{part}', chunk)
                        chunk, part = '', part + 1
                    chunk += para[:6000] + '\n\n'
                if chunk.strip():
                    self.add(f.name, f'{i}.{part}', chunk)
        self.df = Counter(t for p in self.passages for t in set(p['_tokens']))
        self.avg = sum(len(p['_tokens']) for p in self.passages) / max(1, len(self.passages))
    def add(self, filename, part, text):
        self.passages.append({'id': filename + '#' + part, 'kind': 'historical_conversation' if filename.startswith('conversation-') else 'document', 'title': filename, 'content': text.strip(), '_tokens': tokens(text)})
    def search(self, query, limit=6):
        ranked = []
        for p in self.passages:
            counts = Counter(p['_tokens'])
            score = 0
            for t in set(tokens(query)):
                freq = counts[t]
                score += math.log(1 + (len(self.passages) - self.df[t] + .5) / (self.df[t] + .5)) * freq * 2.2 / (freq + 1.2 * (.25 + .75 * len(p['_tokens']) / max(1, self.avg)))
            if score:
                ranked.append(({k: v for k, v in p.items() if not k.startswith('_')}, score))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [dict(p, score=round(s, 3)) for p, s in ranked[:limit]]
