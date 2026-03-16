# Vorbereitung Montag — Dennis & Sebastian
## 09:00–10:30 (Selbststudium)

**Thema:** Claude Agent SDK + Tool Use — Setup und Theorie-Vertiefung

> Ahmad startet eure Session nach den Beginners. Nutzt die Zeit bis dahin, um alles einzurichten und die Pflichtlektüre durchzuarbeiten. Wer das hier gemacht hat, verschwendet in der Lecture KEINE Zeit mit Setup.

---

## Teil 1: Technisches Setup (20 Minuten)

### Schritt 1: Python Environment

```bash
# Neues Verzeichnis fuer heute
mkdir woche3-montag-agent
cd woche3-montag-agent

# Virtual Environment erstellen
python -m venv venv

# Aktivieren
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Pakete installieren
pip install anthropic tiktoken python-dotenv
```

### Schritt 2: API Key einrichten

1. Geht zu: https://console.anthropic.com/settings/keys
2. Erstellt einen neuen API Key (falls ihr keinen habt)
3. Erstellt eine `.env` Datei in eurem Projektordner:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-api03-EUER-KEY-HIER
```

4. Erstellt eine `.gitignore` Datei:

```bash
# .gitignore
.env
venv/
__pycache__/
```

### Schritt 3: Verbindung testen

Erstellt `test_connection.py`:

```python
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

# Einfacher Test: Funktioniert die API?
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=100,
    messages=[
        {"role": "user", "content": "Sag 'Verbindung steht!' auf Deutsch."}
    ]
)

print(response.content[0].text)
print(f"Tokens verwendet: {response.usage.input_tokens + response.usage.output_tokens}")
```

```bash
python test_connection.py
```

Wenn ihr `Verbindung steht!` seht → alles klar.

**Wenn Fehler:** Screenshot machen und an Ahmad schicken.

---

## Teil 2: Pflichtlektüre — Anthropic Tool Use (30 Minuten)

### Lest diese Seite komplett:
**https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview**

Konzentriert euch auf:
1. **Wie definiert man ein Tool?** (JSON Schema mit `name`, `description`, `input_schema`)
2. **Wie sendet man Tools an die API?** (Der `tools` Parameter in `messages.create()`)
3. **Was kommt zurück wenn Claude ein Tool verwenden will?** (`stop_reason: "tool_use"`, `tool_use` Block mit `id`, `name`, `input`)
4. **Wie schickt man das Tool-Ergebnis zurück?** (`tool_result` Message mit der Tool-Use `id`)

### Verstaendnisfragen (schreibt die Antworten auf!)

1. Was ist der Unterschied zwischen `stop_reason: "end_turn"` und `stop_reason: "tool_use"`?
2. Warum hat jeder `tool_use` Block eine eindeutige `id`?
3. Was passiert, wenn das `input_schema` falsch definiert ist?
4. Kann Claude mehrere Tools gleichzeitig aufrufen? Wenn ja, wie?
5. Was ist `tool_choice` und wofuer braucht man das?

---

## Teil 3: Agent Loop verstehen (20 Minuten)

### Das Kernkonzept

Ein einfacher API-Call:
```
User → LLM → Antwort (fertig)
```

Ein Agent:
```
User → LLM → "Ich brauche Tool X" → Tool ausfuehren → Ergebnis an LLM →
LLM → "Ich brauche Tool Y" → Tool ausfuehren → Ergebnis an LLM →
LLM → Finale Antwort (fertig)
```

Der Agent Loop ist eine **while-Schleife**:
```
while stop_reason == "tool_use":
    1. Extrahiere Tool-Name und Input aus der Response
    2. Fuehre das Tool lokal aus
    3. Schicke das Ergebnis als tool_result zurueck
    4. Claude antwortet erneut (entweder mit neuem Tool oder finaler Antwort)
```

**Zeichnet diesen Loop als Diagramm auf Papier.** Wirklich. Mit Pfeilen. Ihr werdet ihn heute implementieren.

### Denk-Aufgabe

Stellt euch vor, ihr baut einen Agent mit diesen 3 Tools:
- `web_suche` — Sucht im Internet
- `rechner` — Berechnet Mathe-Ausdruecke
- `zusammenfassung` — Fasst langen Text zusammen

Ein User fragt: *"Wie hoch ist der Eiffelturm in Metern und was ist das in Fuss?"*

**Schreibt auf:**
1. Welche Tools wuerde der Agent in welcher Reihenfolge aufrufen?
2. Was waere der Input fuer jedes Tool?
3. Wie viele Schleifendurchlaeufe braucht der Agent?

---

## Teil 4: Euren Freitags-Code reviewen (15 Minuten)

Schaut euch nochmal den Agent-Theorie-Code von Freitag an:
- Die 6 Anthropic Patterns (welches Pattern bauen wir heute? → Antwort: Autonomous Agent mit Tool Use)
- Tool Use Architektur (JSON Schema → tool_use → tool_result)
- Structured Output mit tool_choice

**Frage fuer die Lecture:** Ueberlegt euch, welches Tool IHR gerne in einem Agent haettet. Etwas Praktisches. Ahmad fragt euch das um 12:30.

---

## Checkliste — Bin ich bereit?

- [ ] Python venv erstellt und aktiviert
- [ ] `anthropic` und `tiktoken` installiert
- [ ] `.env` mit API Key erstellt
- [ ] `.gitignore` erstellt
- [ ] `test_connection.py` laeuft erfolgreich
- [ ] Tool Use Dokumentation gelesen
- [ ] 5 Verstaendnisfragen beantwortet (schriftlich!)
- [ ] Agent Loop als Diagramm gezeichnet
- [ ] Denk-Aufgabe (Eiffelturm) beantwortet
- [ ] Eigene Tool-Idee ueberlegt

**Wenn alles gecheckt ist: Ihr seid bereit fuer die Lecture mit Ahmad.**
