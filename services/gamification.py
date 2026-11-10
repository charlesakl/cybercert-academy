"""Deterministic achievements from saved learning evidence (not page views)."""
from collections import defaultdict
from datetime import date, timedelta


def calculate(completed, history, reviews, activity_days=None):
    completed = set(completed)
    history = list(history)
    reviews = dict(reviews)
    activity_days = set(activity_days or [])
    xp = 20 * len(completed) + 5 * len(reviews)
    xp += sum(10 * int(x.get('result', {}).get('correct', 0)) for x in history)
    xp += sum(25 for x in history if x.get('mode') == 'mock' and x.get('result', {}).get('percent', 0) >= 80)
    level = 1 + xp // 500
    today = date.today()
    parsed = set()
    for day in activity_days:
        try:
            parsed.add(date.fromisoformat(day))
        except (ValueError, TypeError):
            continue
    streak = 0
    cursor = today if today in parsed else today - timedelta(days=1)
    while cursor in parsed:
        streak += 1
        cursor -= timedelta(days=1)
    badges = []
    if completed: badges.append(('First Steps', 'Review your first lesson'))
    if len(completed) >= 5: badges.append(('Knowledge Explorer', 'Review five lessons'))
    if any(x.get('mode') == 'practice' for x in history): badges.append(('Practice Starter', 'Complete a domain drill'))
    if any(x.get('mode') == 'mock' for x in history): badges.append(('Exam Challenger', 'Complete a mock exam'))
    if any(x.get('mode') == 'mock' and x.get('result', {}).get('percent', 0) >= 80 for x in history):
        badges.append(('Mock Milestone', 'Reach 80% on a mock exam'))
    if len(reviews) >= 10: badges.append(('Recall Builder', 'Review ten distinct flashcards'))
    if streak >= 3: badges.append(('Consistent Learner', 'Study three consecutive days'))
    return {'xp': xp, 'level': level, 'streak': streak, 'badges': badges, 'lessons': len(completed)}
