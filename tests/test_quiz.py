from collections import Counter
from datetime import date
from services.content import load
from services.quiz import prepare,score
from services.flashcards import next_review

def test_bank_complete():
 q=load('questions')
 assert len(q)==110
 assert Counter(x['mode'] for x in q)=={'drill':60,'mock':50}
 assert Counter(x['domain_id'] for x in q if x['mode']=='mock')=={'D1':12,'D2':9,'D3':10,'D4':11,'D5':8}
 assert len(set(x['id'] for x in q))==110
 for item in q:
  assert item['verification_status']=='source_matched'
  assert item['stem'] and item['explanation'] and item['source_page'] and item['answer_page']
  assert [x['id'] for x in item['options']]==['A','B','C','D']
  assert item['correct_option_id'] in ('A','B','C','D')

def test_shuffle_keeps_answer_keys():
 q=load('questions')[:12]
 a=prepare(q,seed=9)
 assert score(a,{x['id']:x['correct_option_id'] for x in a})['correct']==12
 assert score(a,{})['correct']==0

def test_spaced_repetition():
 today=date(2026,11,10)
 assert (next_review(today,0,True)[0]-today).days==1
 assert (next_review(today,1,True)[0]-today).days==3
 assert (next_review(today,2,True)[0]-today).days==7
 assert next_review(today,2,False)[1]==0
