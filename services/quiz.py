"""Pure quiz helpers: original source answers remain stable when options shuffle."""
from collections import defaultdict
import random

def prepare(questions, seed=None, shuffle_questions=True):
    rng=random.Random(seed)
    items=[dict(q,options=[dict(o) for o in q['options']]) for q in questions]
    if shuffle_questions:rng.shuffle(items)
    for q in items:rng.shuffle(q['options'])
    return items

def score(items,answers):
    by_domain=defaultdict(lambda:[0,0]);correct=0
    for q in items:
        hit=answers.get(q['id'])==q['correct_option_id']
        correct+=int(hit)
        by_domain[q['domain_id']][0]+=int(hit)
        by_domain[q['domain_id']][1]+=1
    return {'correct':correct,'total':len(items),'percent':round(100*correct/len(items),1) if items else 0,
            'domains':dict(by_domain)}
