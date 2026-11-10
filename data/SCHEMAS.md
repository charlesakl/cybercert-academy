# Content contracts — Phase 2

The source baseline is `data/source/cc_baseline_claude_2026.pdf` (independent study guide supplied by the user).

- `domains.json`: `id`, `title`, `exam_weight_percent`.
- `study_plan.json`: `day`, `focus`, `task`, `source_page`.
- `lessons.json`: `id`, `domain_id`, `title`, `body`, `source_page`, `source_type`, `status`.
- `questions.json`: `id`, `domain_id`, `mode` (`drill` or `mock`), `stem`, `options` (four `{id,text}`), `correct_option_id`, `explanation`, `source_question_number`, `source_page`, `answer_page`, `verification_status` (`source_matched`). Total 110 = 60 drill + 50 mock.
- `flashcards.json`: `id`, `domain_id`, `front`, `back`, `source_page`, `verification_status` (`source_based_summary`). Total 25 independently summarized study cards; not additional PDF questions.

Question IDs and answer keys remain stable when options are shuffled. Source page numbers refer to the supplied PDF's physical pages.
