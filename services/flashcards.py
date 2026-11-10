"""Lightweight session review scheduling; durable storage follows in Phase 3."""
from datetime import date,timedelta

def next_review(today:date,successful_reviews:int,remembered:bool):
    if not remembered:return today+timedelta(days=1),0
    interval=[1,3,7][min(successful_reviews,2)]
    return today+timedelta(days=interval),successful_reviews+1
