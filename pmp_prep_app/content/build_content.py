#!/usr/bin/env python3
"""Compile the original content sources into the app's bundled JSON asset.

Usage: python3 build_content.py   (writes ../android/app/src/main/assets/content.json)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lessons import TASKS, LESSONS            # noqa: E402
from questions import QUESTIONS, CASES        # noqa: E402
from directory import RESOURCES, INSTITUTIONS, FAQS, REVISION, VERIFIED  # noqa: E402

ECO = "ECO-2026-07"
CONTENT_VERSION = 1


def build():
    tasks = [dict(id=f"{d}-T{n}", domain=d, number=n, title=t) for d, n, t in TASKS]
    titles = {t["id"]: t["title"] for t in tasks}
    lessons, cards = [], []
    for i, l in enumerate(LESSONS, 1):
        lessons.append(dict(id=f"L{i:03d}", taskId=l["task"], title=titles[l["task"]], summary=l["summary"],
                            body=l["body"], keyTerms=[dict(term=a, definition=b) for a, b in l["terms"]],
                            example=l["example"], approachNote=l["approach"], examTip=l["tip"], minutes=l["minutes"]))
        for j, (term, definition) in enumerate(l["terms"], 1):
            cards.append(dict(id=f"F{i:03d}-{j}", taskId=l["task"], front=term, back=definition))
    bundle = dict(
        eco=ECO, contentVersion=CONTENT_VERSION, tasks=tasks, lessons=lessons, flashcards=cards,
        faqs=[dict(id=f"Q{i:02d}", question=q, answer=a) for i, (q, a) in enumerate(FAQS, 1)],
        revision=[dict(term=a, definition=b) for a, b in REVISION],
        cases=CASES, questions=QUESTIONS,
        resources=[dict(r, lastVerified=VERIFIED) for r in RESOURCES],
        institutions=INSTITUTIONS,
    )
    out = os.path.join(HERE, "..", "android", "app", "src", "main", "assets", "content.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=1)
    by_dom = {}
    for q in QUESTIONS:
        by_dom[q["domain"]] = by_dom.get(q["domain"], 0) + 1
    by_type = {}
    for q in QUESTIONS:
        by_type[q["type"]] = by_type.get(q["type"], 0) + 1
    pred = sum(1 for q in QUESTIONS if q["approach"] == "PREDICTIVE")
    print(f"tasks={len(tasks)} lessons={len(lessons)} flashcards={len(cards)} faqs={len(FAQS)} "
          f"questions={len(QUESTIONS)} cases={len(CASES)} resources={len(RESOURCES)} institutions={len(INSTITUTIONS)}")
    print("by domain:", by_dom, "| by type:", by_type, f"| predictive {pred * 100 // len(QUESTIONS)}%")


if __name__ == "__main__":
    build()
