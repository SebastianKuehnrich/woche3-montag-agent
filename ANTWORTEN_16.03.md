# Antworten — Vorbereitung 16.03.

---

## Teil 2: Verständnisfragen — Anthropic Tool Use

### 1. Was ist der Unterschied zwischen `stop_reason: "end_turn"` und `stop_reason: "tool_use"`?

| `stop_reason`  | Bedeutung |
|----------------|-----------|
| `"end_turn"`   | Claude ist **fertig** und hat eine finale Antwort generiert. Es wird kein weiterer Input erwartet. Die Konversation kann enden oder der User stellt eine neue Frage. |
| `"tool_use"`   | Claude möchte ein **Tool aufrufen**, bevor es eine finale Antwort gibt. Die Response enthält einen `tool_use`-Block mit `id`, `name` und `input`. Der Entwickler muss das Tool lokal ausführen und das Ergebnis als `tool_result` zurückschicken. |

**Defensive Coding Relevanz:** Man **muss** den `stop_reason` prüfen, um zu entscheiden, ob die Agent-Loop weiterläuft oder stoppt. Ohne diese Prüfung würde der Agent entweder zu früh abbrechen oder endlos laufen.

```python
# Best Practice: Explizite Prüfung
if response.stop_reason == "tool_use":
    # Tool ausführen und Ergebnis zurückschicken
    pass
elif response.stop_reason == "end_turn":
    # Finale Antwort ausgeben
    pass
else:
    # Defensive: Unerwarteten stop_reason loggen
    logging.warning(f"Unerwarteter stop_reason: {response.stop_reason}")
```

---

### 2. Warum hat jeder `tool_use` Block eine eindeutige `id`?

Die eindeutige `id` dient der **Zuordnung von Tool-Aufruf zu Tool-Ergebnis**.

**Gründe:**

1. **Eindeutige Zuordnung:** Claude kann in einer einzigen Response **mehrere Tools gleichzeitig** aufrufen (Parallel Tool Use). Die `id` stellt sicher, dass jedes `tool_result` dem richtigen `tool_use` zugeordnet wird.
2. **Konsistenz in der Message-History:** Die API erwartet, dass jede `tool_result`-Nachricht die exakte `tool_use_id` referenziert. Ohne korrekte Zuordnung lehnt die API den Request ab.
3. **Fehlerbehandlung:** Falls ein Tool fehlschlägt, kann man über die `id` gezielt berichten, welches Tool betroffen ist.

```python
# Beispiel: tool_use Block
{
    "type": "tool_use",
    "id": "toolu_01ABC123",       # <-- Eindeutige ID
    "name": "rechner",
    "input": {"ausdruck": "330 * 3.28084"}
}

# Zugehöriges tool_result MUSS dieselbe ID verwenden:
{
    "type": "tool_result",
    "tool_use_id": "toolu_01ABC123",  # <-- Muss matchen!
    "content": "1082.68"
}
```

**Defensive Coding:** Immer die `id` direkt aus dem `tool_use`-Block extrahieren, niemals hardcoden oder raten.

---

### 3. Was passiert, wenn das `input_schema` falsch definiert ist?

Mehrere Probleme können auftreten:

| Problem | Auswirkung |
|---------|------------|
| **Fehlende required-Felder** | Claude könnte Parameter weglassen, die das Tool eigentlich braucht → Runtime-Fehler im Tool |
| **Falscher Datentyp** | Claude liefert z.B. einen String statt einer Zahl → Tool crasht oder liefert falsche Ergebnisse |
| **Fehlende/ungenaue Description** | Claude versteht nicht, wofür das Tool da ist, und ruft es falsch oder gar nicht auf |
| **Schema-Syntaxfehler** | Die API wirft einen Validierungsfehler (400 Bad Request) noch bevor Claude antworten kann |
| **Zu lockeres Schema** | Claude hat zu viel Spielraum und sendet unerwartete Inputs |

**Defensive Coding Best Practice:**

```python
# Input IMMER validieren, auch wenn das Schema korrekt aussieht
def rechner(ausdruck: str) -> str:
    if not isinstance(ausdruck, str):
        return "FEHLER: ausdruck muss ein String sein"
    if len(ausdruck) > 200:
        return "FEHLER: Ausdruck zu lang"
    # Nur sichere Zeichen erlauben
    erlaubt = set("0123456789+-*/.(). ")
    if not all(c in erlaubt for c in ausdruck):
        return "FEHLER: Ungültige Zeichen im Ausdruck"
    try:
        ergebnis = eval(ausdruck)  # Vorsicht: nur mit Whitelist!
        return str(ergebnis)
    except Exception as e:
        return f"FEHLER: Berechnung fehlgeschlagen: {e}"
```

---

### 4. Kann Claude mehrere Tools gleichzeitig aufrufen? Wenn ja, wie?

**Ja!** Das nennt sich **Parallel Tool Use**.

Claude kann in einer einzigen Response **mehrere `tool_use`-Blöcke** zurückgeben, wenn die Aufrufe voneinander unabhängig sind.

**Beispiel-Response mit 2 parallelen Tool-Aufrufen:**

```json
{
  "stop_reason": "tool_use",
  "content": [
    {"type": "text", "text": "Ich suche beides gleichzeitig..."},
    {
      "type": "tool_use",
      "id": "toolu_01A",
      "name": "web_suche",
      "input": {"query": "Höhe Eiffelturm Meter"}
    },
    {
      "type": "tool_use",
      "id": "toolu_01B",
      "name": "web_suche",
      "input": {"query": "Wetter Paris heute"}
    }
  ]
}
```

**Handling im Code:**

```python
# Alle tool_use Blöcke aus der Response extrahieren
tool_calls = [block for block in response.content if block.type == "tool_use"]

# Alle Tools ausführen (potenziell parallel)
results = []
for tool_call in tool_calls:
    result = execute_tool(tool_call.name, tool_call.input)
    results.append({
        "type": "tool_result",
        "tool_use_id": tool_call.id,
        "content": result
    })

# ALLE Ergebnisse in EINER Message zurückschicken
messages.append({"role": "user", "content": results})
```

**Wichtig:** Man kann Parallel Tool Use deaktivieren mit `tool_choice: {"type": "any", "disable_parallel_tool_use": true}`.

---

### 5. Was ist `tool_choice` und wofür braucht man das?

`tool_choice` steuert, **ob und wie** Claude Tools verwenden darf.

| Wert | Verhalten |
|------|-----------|
| `{"type": "auto"}` | **(Default)** Claude entscheidet selbst, ob ein Tool nötig ist oder eine direkte Antwort reicht |
| `{"type": "any"}` | Claude **muss** mindestens ein Tool aufrufen — eine reine Textantwort ist nicht erlaubt |
| `{"type": "tool", "name": "rechner"}` | Claude **muss** genau dieses eine Tool verwenden |

**Anwendungsfälle:**

- **`auto`**: Standard-Agent, der flexibel entscheidet
- **`any`**: Wenn man sicherstellen will, dass immer ein Tool-Ergebnis kommt (z.B. Structured Output)
- **`tool` + Name**: Wenn man Claude zwingen will, ein bestimmtes Tool zu benutzen (z.B. für ein Klassifikations-Tool, das immer ein strukturiertes JSON liefern soll)

```python
# Beispiel: Structured Output erzwingen
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=500,
    tools=[sentiment_tool],
    tool_choice={"type": "tool", "name": "analyse_sentiment"},
    messages=[{"role": "user", "content": "Bewerte: 'Das Essen war fantastisch!'"}]
)
```

---

## Teil 3: Denk-Aufgabe — Eiffelturm

**Frage:** *"Wie hoch ist der Eiffelturm in Metern und was ist das in Fuß?"*

### 1. Welche Tools würde der Agent in welcher Reihenfolge aufrufen?

| Durchlauf | Tool | Grund |
|-----------|------|-------|
| 1 | `web_suche` | Höhe des Eiffelturms in Metern herausfinden |
| 2 | `rechner` | Meter in Fuß umrechnen (Ergebnis × 3.28084) |

**`zusammenfassung` wird NICHT benötigt** — die Antwort ist kurz genug, es gibt keinen langen Text zum Zusammenfassen.

### 2. Was wäre der Input für jedes Tool?

```
Durchlauf 1 — web_suche:
  Input: {"query": "Höhe Eiffelturm in Metern"}
  Erwartetes Ergebnis: "330 Meter (mit Antenne)"

Durchlauf 2 — rechner:
  Input: {"ausdruck": "330 * 3.28084"}
  Erwartetes Ergebnis: "1082.68"
```

### 3. Wie viele Schleifendurchläufe braucht der Agent?

**3 Durchläufe insgesamt:**

1. **Durchlauf 1:** Claude erhält die User-Frage → ruft `web_suche` auf → `stop_reason: "tool_use"`
2. **Durchlauf 2:** Claude erhält das Suchergebnis → ruft `rechner` auf → `stop_reason: "tool_use"`
3. **Durchlauf 3:** Claude erhält das Rechenergebnis → formuliert finale Antwort → `stop_reason: "end_turn"`

```
User-Frage
  → LLM: "Ich brauche web_suche" (stop_reason: tool_use)     ← Durchlauf 1
  → Tool-Ergebnis: "330 Meter"
  → LLM: "Ich brauche rechner" (stop_reason: tool_use)        ← Durchlauf 2
  → Tool-Ergebnis: "1082.68"
  → LLM: "Der Eiffelturm ist 330m / 1082.68ft" (end_turn)     ← Durchlauf 3
```

**Hinweis:** Es ist auch möglich, dass Claude die Umrechnung selbst macht, ohne den `rechner` aufzurufen — dann wären es nur 2 Durchläufe. Die Tool-Nutzung hängt davon ab, wie Claude die Situation einschätzt.

---

## Teil 4: Eigene Tool-Idee

**Vorschlag: `dateien_suche`** — Ein Tool, das lokale Dateien nach Inhalt oder Name durchsucht.

- **Input:** `{"suchbegriff": "API Key", "verzeichnis": "./src", "dateityp": ".py"}`
- **Output:** Liste der Dateien mit Zeilennummern, die den Suchbegriff enthalten
- **Nutzen:** Ein Agent könnte damit selbstständig eine Codebasis analysieren, Bugs finden oder Refactoring vorschlagen.

---

## Checkliste-Status

- [x] Python venv erstellt und aktiviert
- [x] `anthropic` und `tiktoken` installiert
- [x] `.env` mit API Key erstellt
- [x] `.gitignore` erstellt
- [x] `test_connection.py` läuft erfolgreich
- [x] Tool Use Dokumentation gelesen
- [x] 5 Verständnisfragen beantwortet (schriftlich!)
- [x] Agent Loop als Diagramm beschrieben
- [x] Denk-Aufgabe (Eiffelturm) beantwortet
- [x] Eigene Tool-Idee überlegt
