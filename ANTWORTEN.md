# Antworten — Vorbereitung Montag 16.03.

## Teil 2: Verständnisfragen

### 1. Was ist der Unterschied zwischen `stop_reason: "end_turn"` und `stop_reason: "tool_use"`?

| | `"end_turn"` | `"tool_use"` |
|---|---|---|
| **Bedeutung** | Claude ist fertig und liefert eine finale Textantwort | Claude braucht ein Tool, bevor es antworten kann |
| **Was tun?** | Antwort aus `response.content` extrahieren und dem User anzeigen | Tool ausführen, Ergebnis als `tool_result` zurückschicken, nächste Iteration starten |
| **Loop-Verhalten** | Loop endet | Loop läuft weiter |

```python
# Entscheidungslogik im Code:
if response.stop_reason == "end_turn":
    # Finale Antwort → Loop beenden
    return response.content[0].text

elif response.stop_reason == "tool_use":
    # Tool ausführen → Ergebnis zurückschicken → weiter im Loop
    tool_result = execute_tool(block.name, block.input)
    messages.append({"role": "user", "content": [{"type": "tool_result", ...}]})
```

---

### 2. Warum hat jeder `tool_use` Block eine eindeutige `id`?

Die `id` verknüpft einen **Tool-Aufruf** mit seinem **Ergebnis**. Das ist notwendig, weil Claude **mehrere Tools in einer einzigen Response** aufrufen kann.

Ohne IDs wüsste die API nicht, welches Ergebnis zu welchem Aufruf gehört.

**Beispiel:**
```
Response von Claude:
  tool_use  id="toolu_abc"  → rechner("2+2")
  tool_use  id="toolu_xyz"  → web_suche("Python")

Unsere Antwort:
  tool_result  tool_use_id="toolu_abc"  → "4"
  tool_result  tool_use_id="toolu_xyz"  → "Python ist eine Programmiersprache..."
```

Ohne die ID-Zuordnung könnte Claude nicht wissen, dass `"4"` die Antwort auf den Rechner und nicht auf die Websuche ist.

---

### 3. Was passiert, wenn das `input_schema` falsch definiert ist?

Mehrere Probleme können auftreten:

1. **Fehlende `required`-Felder** → Claude lässt Parameter weg, die das Tool eigentlich braucht → `KeyError` oder leere Werte
2. **Falscher Datentyp** (z.B. `"type": "string"` statt `"type": "number"`) → Claude sendet einen String wo eine Zahl erwartet wird → `TypeError`
3. **Fehlende/ungenaue `description`** → Claude versteht nicht, was das Tool tut oder welche Werte erwartet werden → falsche oder unsinnige Tool-Aufrufe
4. **Schema zu vage** → Claude erfindet Parameter, die das Tool nicht kennt
5. **Schema komplett kaputt** (ungültiges JSON Schema) → API wirft einen Validierungsfehler (400 Bad Request)

**Defensive Maßnahme:** Inputs im Tool **immer validieren** — nie davon ausgehen, dass der Input dem Schema entspricht:

```python
def tool_rechner(ausdruck: str) -> str:
    if not isinstance(ausdruck, str) or not ausdruck.strip():
        return "Fehler: Leerer Ausdruck."
    # ... weitere Validierung
```

---

### 4. Kann Claude mehrere Tools gleichzeitig aufrufen? Wenn ja, wie?

**Ja.** Claude kann in einer einzigen Response mehrere `tool_use`-Blöcke senden. Die `response.content`-Liste enthält dann mehrere Einträge:

```python
response.content = [
    TextBlock(type="text", text="Ich suche die Höhe und rechne um..."),
    ToolUseBlock(type="tool_use", id="toolu_1", name="web_suche",
                 input={"query": "Eiffelturm Höhe"}),
    ToolUseBlock(type="tool_use", id="toolu_2", name="rechner",
                 input={"ausdruck": "330 * 3.28084"}),
]
```

**Wichtig für unseren Code:** Wir müssen **alle** `tool_use`-Blöcke in einer Schleife verarbeiten und die Ergebnisse als **Liste** von `tool_result`-Objekten zurückschicken:

```python
tool_results = []
for block in response.content:
    if block.type == "tool_use":
        result = execute_tool(block.name, block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": result,
        })

messages.append({"role": "user", "content": tool_results})
```

---

### 5. Was ist `tool_choice` und wofür braucht man das?

`tool_choice` steuert, **ob und welches Tool** Claude verwenden soll:

| Wert | Verhalten |
|---|---|
| `{"type": "auto"}` | **(Standard)** Claude entscheidet selbst, ob es ein Tool braucht |
| `{"type": "any"}` | Claude **muss** ein Tool verwenden (egal welches) |
| `{"type": "tool", "name": "rechner"}` | Claude **muss genau dieses** Tool verwenden |

**Wichtigster Anwendungsfall — Structured Output:**

Man definiert ein "Ausgabe-Tool" mit dem gewünschten Schema und erzwingt dessen Nutzung. So erhält man **garantiert strukturierte Daten** statt Freitext:

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    tools=[{
        "name": "ergebnis",
        "description": "Strukturierte Ausgabe",
        "input_schema": {
            "type": "object",
            "properties": {
                "antwort": {"type": "string"},
                "konfidenz": {"type": "number"},
            },
            "required": ["antwort", "konfidenz"],
        },
    }],
    tool_choice={"type": "tool", "name": "ergebnis"},
    messages=[{"role": "user", "content": "Was ist 2+2?"}],
)
# response.content[0].input → {"antwort": "4", "konfidenz": 1.0}
```

---

## Teil 3: Denk-Aufgabe — Eiffelturm

**Frage:** *"Wie hoch ist der Eiffelturm in Metern und was ist das in Fuß?"*

### Ablauf des Agents:

```
Iteration 1:
  User → Claude
  Claude → tool_use: web_suche(query="Eiffelturm Höhe Meter")
  Tool-Ergebnis → "Der Eiffelturm ist 330 Meter hoch..."

Iteration 2:
  Claude → tool_use: rechner(ausdruck="330 * 3.28084")
  Tool-Ergebnis → "Ergebnis: 1082.6772"

Iteration 3:
  Claude → end_turn: "Der Eiffelturm ist 330 Meter hoch,
           das entspricht ca. 1.082,68 Fuß."
```

### Antworten:

1. **Welche Tools in welcher Reihenfolge?**
   - Zuerst `web_suche` (Höhe in Metern herausfinden)
   - Dann `rechner` (Meter in Fuß umrechnen)
   - `zusammenfassung` wird **nicht** benötigt

2. **Input für jedes Tool?**
   - `web_suche` → `{"query": "Eiffelturm Höhe Meter"}`
   - `rechner` → `{"ausdruck": "330 * 3.28084"}`

3. **Wie viele Schleifendurchläufe?**
   - **3 Durchläufe** (2× `tool_use` + 1× `end_turn`)
   - Alternativ **2 Durchläufe**, wenn Claude die Höhe bereits kennt und beide Tools parallel aufruft

---

## Teil 4: Welches Pattern bauen wir heute?

**Autonomous Agent mit Tool Use** — eines der 6 Anthropic Patterns.

Der Agent nutzt eine While-Schleife (Agent Loop), um selbstständig zu entscheiden, welche Tools er braucht, führt sie aus und iteriert bis zur finalen Antwort. Die Architektur:

```
JSON Schema (Tool-Definition)
    → tools-Parameter an API senden
    → Claude antwortet mit tool_use-Block
    → Wir führen das Tool lokal aus
    → tool_result zurückschicken
    → Wiederholen bis end_turn
```
