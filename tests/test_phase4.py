from datetime import date, timedelta
import pytest
from services.ai import retrieve_context, ask_tutor, TutorError
from services.gamification import calculate
from services.progress import serialize, deserialize


def test_retrieval_grounded():
    lessons = [
        {'id': 'D1-P05', 'source_page': 5, 'body': 'Confidentiality encryption access controls'},
        {'id': 'D2-P08', 'source_page': 8, 'body': 'Business continuity disaster recovery RTO RPO'},
    ]
    context, sources = retrieve_context('Explain RTO and disaster recovery', lessons)
    assert sources == ['D2-P08']
    assert 'PDF page 8' in context


def test_tutor_requires_configuration():
    with pytest.raises(TutorError):
        ask_tutor('Explain RBAC', [], {})


def test_gamification_is_deterministic():
    today = date.today().isoformat()
    stats = calculate({'D1-P05'}, [{'mode':'practice','result':{'correct':3,'total':5,'percent':60}}], {}, [today])
    assert stats['xp'] == 50
    assert stats['streak'] == 1
    assert len(stats['badges']) == 2


def test_gamification_yesterday_streak():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert calculate(set(), [], {}, [yesterday])['streak'] == 1


def test_progress_v1_backwards_compatible():
    legacy = {'version':1,'completed':['D1-P05'],'current_lesson':'D1-P05','practice_history':[],'flashcard_reviews':{}}
    restored = deserialize(legacy)
    assert restored['activity_days'] == []
    assert restored['ai_daily_usage'] == {}
    new = serialize(restored)
    assert new['completed'] == ['D1-P05']


def test_tutor_question_length():
    with pytest.raises(TutorError):
        ask_tutor('x', [], {'provider':'openai','api_key':'test','model':'test'})
