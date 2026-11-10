from services.content import load, domain_lessons
def test_five_domains():
    d=load("domains")
    assert len(d)==5
    assert abs(sum(x["exam_weight_percent"] for x in d)-99.9)<0.2
def test_fourteen_days():
    assert [x["day"] for x in load("study_plan")]==list(range(1,15))
def test_lessons_have_provenance():
    assert all(x["source_page"]>0 and x["body"] for x in load("lessons"))
def test_questions_imported():
    assert len(load("questions"))==110
