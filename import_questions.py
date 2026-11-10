"""Reproducible, strict import from the provided independent CC study guide."""
import json,re
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parent
PDF=ROOT/'data/source/cc_baseline_claude_2026.pdf'
if not PDF.exists():
    PDF=Path('/mnt/data/ISC2_CC_2026_Pass_Plan_Study_Guide_Claud.pdf')
doc=fitz.open(PDF)

def page_text(n):
    t=doc[n-1].get_text()
    # Source text from PDF is already in reading order; retain lines.
    return t

def extract_questions(pages,mode,domain):
    found=[]
    for page in pages:
        t=page_text(page)
        t=re.sub(r'ISC2 CC 2026 · Pass Plan & Study Guide · independent material\s*\n\d+\s*$', '',t)
        lines=t.splitlines()
        starts=[i for i,x in enumerate(lines) if re.fullmatch(r'\d{1,2}',x.strip())]
        for k,i in enumerate(starts):
            num=int(lines[i].strip())
            if not (1<=num<= (12 if mode=='drill' else 50)):continue
            end=starts[k+1] if k+1<len(starts) else len(lines)
            chunk=lines[i+1:end]
            opts=[]; stem=[]; cur=None
            for line in chunk:
                m=re.match(r'^([A-D])\.\s+(.+)$',line.strip())
                if m:
                    if cur:opts.append(cur)
                    cur={'id':m.group(1),'text':m.group(2)}
                elif cur:cur['text']+=' '+line.strip()
                else:stem.append(line.strip())
            if cur:opts.append(cur)
            if len(opts)!=4:raise ValueError(f'Question options mismatch {mode} {domain} p{page} #{num}: {len(opts)}')
            found.append({'id':f'{domain}-{mode.upper()}-{num:02d}' if mode=='drill' else f'MOCK-{num:02d}',
              'domain_id':domain,'mode':mode,'stem':' '.join(stem).strip(), 'options':opts,
              'correct_option_id':None,'explanation':None,'source_question_number':num,'source_page':page,
              'answer_page':None,'verification_status':'pending'})
    return found

def drill_answers(page):
    lines=page_text(page).splitlines()
    indices=[i for i,l in enumerate(lines) if re.match(r'^\d{1,2}\. [A-D]\b',l.strip())]
    result={}
    for k,i in enumerate(indices):
        m=re.match(r'^(\d{1,2})\. ([A-D])\b\s*(.*)',lines[i].strip())
        n=int(m.group(1));end=indices[k+1] if k+1<len(indices) else len(lines)
        parts=[m.group(3)]+[x.strip() for x in lines[i+1:end]]
        parts=[x for x in parts if x and not x.startswith(('My score:','ISC2 CC 2026')) and not re.fullmatch(r'\d+',x)]
        result[n]=(m.group(2),' '.join(parts))
    return result

def mock_answers():
    result={}
    for page in [43,44]:
        lines=page_text(page).splitlines()
        indices=[i for i,l in enumerate(lines) if re.match(r'^\d{1,2}\. [A-D]$',l.strip())]
        for k,i in enumerate(indices):
            m=re.match(r'^(\d{1,2})\. ([A-D])$',lines[i].strip())
            n=int(m.group(1)); end=indices[k+1] if k+1<len(indices) else len(lines)
            chunk=[x.strip() for x in lines[i+1:end]]
            domain=next((x for x in chunk if re.fullmatch(r'D[1-5]',x)),None)
            if not domain:raise ValueError(f'Missing domain mock #{n}')
            di=chunk.index(domain)
            tail=chunk[di+1:]
            if 'Domain score tracker' in tail:tail=tail[:tail.index('Domain score tracker')]
            tail=[x for x in tail if x and not x.startswith(('ISC2 CC 2026','Domain score tracker','The colored tag','My score','Pass-ready'))]
            result[n]=(m.group(2),domain,' '.join(tail),page)
    return result

questions=[]
for domain,qs,answer in [('D1',[8,9],10),('D2',[13,14],15),('D3',[19,20],21),('D4',[25,26],27),('D5',[31,32],33)]:
    part=extract_questions(qs,'drill',domain)
    answers=drill_answers(answer)
    if len(part)!=12 or len(answers)!=12:raise ValueError(f'{domain}: questions {len(part)}, answers {len(answers)}')
    for q in part:
        q['correct_option_id'],q['explanation']=answers[q['source_question_number']]
        q['answer_page']=answer;q['verification_status']='source_matched'
    questions.extend(part)
part=extract_questions(range(35,43),'mock','D0')
answers=mock_answers()
if len(part)!=50 or len(answers)!=50:raise ValueError(f'Mock: questions {len(part)}, answers {len(answers)}')
for q in part:
    a,d,exp,p=answers[q['source_question_number']]
    q.update(correct_option_id=a,domain_id=d,explanation=exp,answer_page=p,verification_status='source_matched')
questions+=part
assert len(questions)==110
assert len({q['id'] for q in questions})==110
for q in questions:
    assert q['stem'] and q['explanation'] and q['correct_option_id'] in [o['id'] for o in q['options']]
(ROOT/'data/questions.json').write_text(json.dumps(questions,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Imported',len(questions),'questions',{'drill':60,'mock':50})
for q in questions[:2]+questions[59:61]+questions[-2:]:
 print(q['id'],q['domain_id'],q['correct_option_id'],q['stem'][:50],q['explanation'][:80])
