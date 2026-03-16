# Reflexion — 17.03.2026 | Sebastian

---

## 1. Was habe ich gebaut?

Einen **autonomen Agent mit Tool Use Loop** basierend auf dem Anthropic Claude SDK. Der Agent implementiert Pattern 6 (Autonomous Agent) mit 4 Tools: `rechner` (sichere Mathematik ohne eval), `aktuelles_datum` (Datum/Uhrzeit/Wochentag), `text_analyse` (Wort-/Zeichen-/Satzstatistiken + haeufigste Woerter), und `einheiten_umrechner` (Temperatur, Distanz, Gewicht). Der Agent Loop funktioniert als while-Schleife mit `stop_reason`-Pruefung, Conversation History fuer Gedaechtnis ueber mehrere Fragen, Structured Output via `tool_choice`, und crashsicherem Error Handling.

---

## 2. Fragen beantworten

### 1. Was ist der Unterschied zwischen `stop_reason: "end_turn"` und `stop_reason: "tool_use"`?

- **`end_turn`**: Claude ist fertig und hat eine finale Textantwort generiert. Der Agent Loop endet.
- **`tool_use`**: Claude will ein Tool aufrufen. Die Response enthaelt einen `tool_use`-Block mit `id`, `name` und `input`. Der Entwickler muss das Tool lokal ausfuehren, das Ergebnis als `tool_result` zurueckschicken, und Claude erneut antworten lassen.

Der `stop_reason` steuert die Kontrolllogik des Agent Loops — ohne korrekte Pruefung wuerde der Agent entweder zu frueh abbrechen oder endlos laufen.

### 2. Warum braucht jedes `tool_result` eine `tool_use_id`?

Die `tool_use_id` stellt die **eindeutige Zuordnung** zwischen Tool-Aufruf und Tool-Ergebnis sicher. Das ist besonders wichtig bei **Parallel Tool Use**, wenn Claude mehrere Tools gleichzeitig aufruft. Ohne korrekte ID-Zuordnung koennte Claude das Ergebnis von `rechner` mit dem Ergebnis von `aktuelles_datum` verwechseln. Die API lehnt Requests ab, wenn die IDs nicht matchen.

### 3. Was passiert wenn die `description` eines Tools schlecht formuliert ist?

Claude waehlt das **falsche Tool** oder ruft **gar kein Tool** auf. Die description ist das einzige, was Claude liest, um zu entscheiden, ob ein Tool relevant ist. Das ist wie bei Evaluation-Prompts: Praezision zaehlt. Eine vage description wie "Macht Sachen mit Zahlen" fuehrt dazu, dass Claude den Rechner nicht zuverlaessig fuer Berechnungen waehlt.

**Beispiel:** Wenn die description von `aktuelles_datum` nur "Gibt Datum zurueck" sagt, wird Claude es moeglicherweise nicht aufrufen, wenn nach dem Wochentag gefragt wird.

### 4. Wie viele Tokens hat der Agent fuer Frage 4 (Datum + Rechnung) verbraucht?

**Erwartung:** Ca. 800-1200 Tokens fuer 2-3 Durchlaeufe (beide Tools + finale Antwort).
*(Exakter Wert muss beim Testen ermittelt und hier eingetragen werden.)*

### 5. Was ist `tool_choice` und wie habe ich es in der LLM-as-Judge Evaluation benutzt?

`tool_choice` steuert, **ob und wie** Claude Tools verwenden darf:
- `{"type": "auto"}` — Claude entscheidet selbst (Standard)
- `{"type": "any"}` — Claude MUSS mindestens ein Tool aufrufen
- `{"type": "tool", "name": "..."}` — Claude MUSS genau dieses Tool verwenden

In der **LLM-as-Judge Evaluation** habe ich `tool_choice` mit `{"type": "tool", "name": "analyse_ergebnis"}` benutzt, um Claude zu zwingen, die Bewertung als strukturiertes JSON im definierten Schema zurueckzugeben — Structured Output. Gleiche Technik heute im Gold-Tier mit `strukturierte_analyse()`.

---

## 3. Fragen fuer Ahmad

1. Wie handhabt man in Produktion die wachsende `conversation_history`? Ab wann wird es problematisch (Token-Limit), und was ist die beste Strategie: Sliding Window, Zusammenfassung, oder Token-Counting mit Trim?

2. Gibt es Best Practices fuer Tool-Descriptions die ueber "sei praezise" hinausgehen? Zum Beispiel: Soll man Negativ-Beispiele einbauen ("Verwende dieses Tool NICHT fuer...")? Wie testet man systematisch ob Claude die richtigen Tools waehlt?

---

## 4. CV Bullet Point

```
Built autonomous AI agent with Claude SDK implementing tool-use loop
with 4 specialized tools (calculator, date, text analysis, unit converter),
persistent conversation memory, structured output via tool_choice,
and production-grade error handling with defensive input validation.
```
