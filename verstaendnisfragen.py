"""
verstaendnisfragen.py — Antworten auf die 5 Verständnisfragen + Denk-Aufgabe.

Dieses Modul dokumentiert die Antworten als ausführbare Beispiele,
damit man die Konzepte nicht nur lesen, sondern auch ausprobieren kann.
"""


# ─── Frage 1 ──────────────────────────────────────────────────────────────────
# Was ist der Unterschied zwischen stop_reason: "end_turn" und "tool_use"?
#
# "end_turn" → Claude ist fertig und hat eine finale Textantwort.
#              Die Konversation kann hier enden.
#
# "tool_use" → Claude will ein Tool aufrufen, bevor es antworten kann.
#              Die Response enthält einen tool_use Block mit:
#              - id: Eindeutige ID für diesen Tool-Aufruf
#              - name: Name des gewünschten Tools
#              - input: Die Parameter für das Tool
#              → Wir MÜSSEN das Tool ausführen und das Ergebnis zurückschicken.


# ─── Frage 2 ──────────────────────────────────────────────────────────────────
# Warum hat jeder tool_use Block eine eindeutige ID?
#
# Die ID verknüpft den Tool-Aufruf (tool_use) mit dem Ergebnis (tool_result).
# Claude kann MEHRERE Tools in einer Response aufrufen. Ohne IDs wüsste die
# API nicht, welches Ergebnis zu welchem Aufruf gehört.
#
# Beispiel:
#   tool_use  id="toolu_abc" → rechner(2+2)
#   tool_use  id="toolu_xyz" → web_suche("Python")
#   tool_result tool_use_id="toolu_abc" → "4"
#   tool_result tool_use_id="toolu_xyz" → "Python ist..."


# ─── Frage 3 ──────────────────────────────────────────────────────────────────
# Was passiert, wenn das input_schema falsch definiert ist?
#
# Mögliche Probleme:
# 1. Claude sendet falsche/fehlende Parameter → Tool-Ausführung schlägt fehl
# 2. Required-Felder fehlen im Schema → Claude lässt sie weg
# 3. Falscher Typ (string statt number) → Unerwartete Werte
# 4. Fehlende Description → Claude versteht nicht, was das Tool tut
#
# → Defensive Maßnahme: Input IMMER validieren, auch wenn das Schema korrekt ist.
#   Vertraue nie darauf, dass der Input dem Schema entspricht.


# ─── Frage 4 ──────────────────────────────────────────────────────────────────
# Kann Claude mehrere Tools gleichzeitig aufrufen? Wenn ja, wie?
#
# Ja! Claude kann in einer Response MEHRERE tool_use Blöcke senden.
# Die Response.content ist dann eine Liste mit mehreren Einträgen.
#
# Beispiel-Response:
#   content = [
#       TextBlock(text="Ich suche..."),
#       ToolUseBlock(name="web_suche", input={"query": "..."}),
#       ToolUseBlock(name="rechner", input={"ausdruck": "..."}),
#   ]
#
# → Wir müssen ALLE tool_use Blöcke verarbeiten und die Ergebnisse
#   als Liste von tool_result Objekten zurückschicken.


# ─── Frage 5 ──────────────────────────────────────────────────────────────────
# Was ist tool_choice und wofür braucht man das?
#
# tool_choice steuert, wie Claude Tools auswählt:
#
# - {"type": "auto"} (Standard)
#   → Claude entscheidet selbst ob und welches Tool es nutzt
#
# - {"type": "any"}
#   → Claude MUSS ein Tool verwenden (egal welches)
#
# - {"type": "tool", "name": "rechner"}
#   → Claude MUSS genau dieses Tool verwenden
#
# Anwendungsfall für "tool": Structured Output erzwingen.
# Man definiert ein "Output-Tool" mit dem gewünschten Schema und
# zwingt Claude, es aufzurufen → garantiert strukturierte Ausgabe.


# ─── Denk-Aufgabe: Eiffelturm ────────────────────────────────────────────────
# Frage: "Wie hoch ist der Eiffelturm in Metern und was ist das in Fuß?"
#
# Erwarteter Agent-Ablauf:
#
# Iteration 1:
#   Claude → tool_use: web_suche(query="Eiffelturm Höhe Meter")
#   Ergebnis → "Der Eiffelturm ist 330 Meter hoch..."
#
# Iteration 2:
#   Claude → tool_use: rechner(ausdruck="330 * 3.28084")
#   Ergebnis → "Ergebnis: 1082.6772"
#
# Iteration 3:
#   Claude → end_turn: "Der Eiffelturm ist 330 Meter hoch,
#             das entspricht ca. 1.082,68 Fuß."
#
# → 3 Schleifendurchläufe (2x tool_use + 1x end_turn)
#
# HINWEIS: Claude könnte auch beide Tools in Iteration 1 parallel aufrufen,
# wenn es die Höhe schon kennt. Dann wären es nur 2 Durchläufe.


if __name__ == "__main__":
    print("Verständnisfragen — siehe Kommentare in dieser Datei.")
    print("Starte den Agent mit: python agent.py")
    print()
    print("Teste z.B.:")
    print('  "Wie hoch ist der Eiffelturm in Metern und was ist das in Fuß?"')
