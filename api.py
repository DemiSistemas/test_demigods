import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict

app = FastAPI(title="Demigods Test API")

# Habilitar CORS para permitir llamadas desde Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar el archivo data.json oficial
with open(Path(__file__).with_name("data.json"), encoding="utf-8") as f:
    DATA = json.load(f)

GODS = DATA["gods"]
QUESTIONS = DATA["questions"]
THREE_BIG = {"Zeus", "Poseidón", "Hades"}

CABIN_BY_GOD = {
    "Zeus": 1, "Eolo": 1, "Hera": 2, "Poseidón": 3,
    "Demeter": 4, "Deméter": 4, "Perséfone": 4,
    "Ares": 5, "Deimos": 5, "Fobos": 5,
    "Atenea": 6, "Apolo": 7, "Asclepio": 7, "Higía": 7,
    "Artemisa": 8, "Hefesto": 9, "Afrodita": 10,
    "Hermes": 11, "Hebe": 11, "Jano": 11, "Harmonía": 11,
    "Dionisio": 12, "Hades": 13, "Iris": 14,
    "Hypnos": 15, "Tánatos": 15, "Nix": 15,
    "Némesis": 16, "Hécate": 20,
}

def get_cabin(god: str) -> int:
    return CABIN_BY_GOD.get(god, 11)

def calculate_scores(answers: Dict[str, str]):
    scores = {god: 0 for god in GODS}
    exclude_artemisa = False
    for question, answer in answers.items():
        if question in QUESTIONS and answer in QUESTIONS[question]:
            rule = QUESTIONS[question][answer]
            for god in rule.get("gods", []):
                if god in scores:
                    scores[god] += 1
            if rule.get("action") == "exclude_artemisa":
                exclude_artemisa = True
    return scores, exclude_artemisa

def get_candidates(scores, exclude_artemisa):
    ranked = sorted(scores.items(), key=lambda item: (-item[1], GODS.index(item[0])))
    positive = [(g, s) for g, s in ranked if s > 0]
    if exclude_artemisa:
        positive = [(g, s) for g, s in positive if g != "Artemisa"]
    if not positive:
        return [], ranked, False

    max_score = positive[0][1]
    tied_top = [g for g, s in positive if s == max_score]
    allowed_big = {tied_top[0]} if len(tied_top) == 1 and tied_top[0] in THREE_BIG else set()
    filtered = [(g, s) for g, s in positive if g not in THREE_BIG or g in allowed_big]

    hermes_tie_rule = len(tied_top) >= 3
    if hermes_tie_rule:
        top_allowed = [(g, s) for g, s in filtered if g in tied_top and g != "Hermes"]
        candidates = [("Hermes", scores.get("Hermes", 0))]
        candidates.extend(top_allowed[:2])
        for item in filtered:
            if len(candidates) >= 3:
                break
            if item[0] not in {g for g, _ in candidates}:
                candidates.append(item)
    else:
        candidates = filtered[:3]

    seen = set()
    candidates = [(g, s) for g, s in candidates if not (g in seen or seen.add(g))][:3]
    return candidates, ranked, hermes_tie_rule

class EvaluateRequest(BaseModel):
    answers: Dict[str, str]

# --- ENDPOINTS REST ---

@app.get("/api/questions")
def read_questions():
    """Lee data.json en tiempo real en cada consulta"""
    with open(Path(__file__).with_name("data.json"), encoding="utf-8") as f:
        data = json.load(f)
    return {"questions": data["questions"], "gods": data["gods"]}

@app.post("/api/evaluate")
def evaluate_test(req: EvaluateRequest):
    """Recibe las respuestas de Next.js y calcula el resultado en Python"""
    scores, exclude_artemisa = calculate_scores(req.answers)
    candidates, ranked, hermes_tie_rule = get_candidates(scores, exclude_artemisa)
    
    formatted_candidates = [
        {"god": god, "score": score, "cabin": get_cabin(god)}
        for god, score in candidates
    ]
    return {
        "candidates": formatted_candidates,
        "hermes_tie_rule": hermes_tie_rule,
        "gods": GODS
    }

@app.get("/api/cabin/{god_name}")
def read_cabin(god_name: str):
    return {"god": god_name, "cabin": get_cabin(god_name)}