Recognizer: phone STT. Calibrated on 5,289 real caller turns.

Simulate raw automatic speech recognition, not a careful human transcript. The written caller text is only intended speech. Its spelling, punctuation, capitalization, digit grouping, and prior-call context must not be treated as authoritative evidence.

If a per-turn recognizer draw is supplied for lexical outcome, streaming split, casing, or terminal punctuation, use that draw. Do not re-draw a different class because it feels more likely. The profile’s job is to render the drawn class in this recognizer’s style.

PRIMARY CALIBRATION CORRECTIONS

The largest current mismatch is not “too few errors overall”; it is the shape of the output:

- Too many turns contain numerals. Do not inverse-normalize every spoken number just because the source text contains digits or because a number is semantically present.
- Names: about three in four name-bearing turns keep the complete name exactly. When a name does break, prefer rough phonetic/word-like forms over tidy alternate spellings.
- Digit-bearing material is too damaged overall. Short ZIPs, card endings, dates, and brief numeric fields are usually preserved. Put digit corruption mainly into long identifiers and drawn lexical-error turns; do not damage every numeric field in the same turn.
- Streaming splits are under-produced. Splits occur even when the words are otherwise correct.
- Edge clipping is under-produced. A clipped draw must visibly lose an actual beginning or ending span.
- No-terminal-punctuation is under-produced.
- No-transcription is slightly over-produced. Do not erase extra repeated or closing turns unless the draw is absent.
- The recognizer’s formatting is more ASR-like than edited text: it often uses “Zip” rather than source-style “ZIP,” joins name + demographic fragments with commas, inserts commas in weekday-date phrases, prefers “a.m./p.m.” over “AM/PM,” sometimes uses “OK,” sometimes lowercases branded/product words, and sometimes adds a question mark to declarative-sounding requests.

POOLED TARGETS

Primary outcomes are mutually exclusive:

Outcome                                  Share of all turns
Correct lexical recognition                    77.5%
Minor lexical error                            11.9%
Substantial decoding error                      5.8%
Beginning/end capture clipping                  1.3%
No transcription                                3.5%

Separate properties:
Multiple recognition segments                   6.2%
No terminal punctuation                         9.0%
Entire transcript lowercase                     1.7%
Contains numerals                              35.3%
Contains digit-by-digit number words             1.0%

Content-conditioned fidelity:
Caller names entirely correct                  73.9%
Digit-bearing material preserves all digits     87.0%

All-digit preservation by intended string length:
3–5 digits                                     about 96%
6–9 digits                                     about 96%
10 or more digits                              about 74%

These are measured outputs, not independent corruption passes. A single drawn minor or substantial outcome may account for a damaged name, a damaged number, or an ordinary-word error. Do not stack independent errors just to show effort.

OUTCOME RENDERING

Correct lexical recognition:
- Preserve the spoken words, allowing recognizer punctuation, casing, and inverse-text-normalization.
- Correct does not mean source-identical. It may have different commas, a colon after “date of birth,” “OK” for “Okay,” “Zip” for “ZIP,” “wanna” only if treated as a lexical variant in the draw, or no terminal punctuation if the punctuation draw says so.
- Do not insert homophone errors into correct draws.

Minor lexical error:
- Make one local acoustic discrepancy, or one small identifier/name error.
- Examples: “Sure” → “Share”; “want to” → “wanna”; “leave a message” → “leave the message”; “booking” → “book in”; “had” → “have”; one surname spelling change; one digit lost/substituted in a long identifier.
- The changed material must be real words/recognized tokens, not just punctuation.

Substantial decoding error:
- Damage a localized region unmistakably: several digits, a name reanalyzed into words, a context-poor phrase decoded as something else, or a partial restart/overlap.
- Surrounding ordinary words may remain accurate.
- Rarely include foreign-language or phonetic fragments in number/name regions. Keep these rare and localized.

Clipped:
- Remove an actual beginning or ending span. Do not mark the loss with ellipses.
- Valid clipping examples:
  - “Uh, I don’t have the city handy…” → “Don’t have the city handy…”
  - “Jordan Lee. My date of birth is…” → “My date of birth is…”
  - “Yes, Monday August tenth, 8am to 12pm” → “Monday, August 10th, 8 a.m. to 12 p.m.”
  - lose the final year or final callback phrase.
- A clipped turn can otherwise be clean and punctuated normally.

Absent:
- Produce no transcription only when the draw is absent.
- Allocate absent outcomes disproportionately to repeated confirmations, brief acknowledgments, second goodbyes, unfinished final fragments, and repeated “that’s all” turns.
- Still allow occasional substantive complete sentences to disappear.
- Do not over-erase closings: many “Thank you, that’s all I needed” turns transcribe normally.

NAMES

About one in four name-bearing turns fails to recover the complete intended name; the other three in four keep it exactly. A name breaks only on a turn whose draw is minor or substantial, never on outcome=correct, and not on every such turn.

Do not merely normalize unfamiliar names to a nearby common surname every time. This recognizer often produces rough acoustic forms, word-like substitutions, lowercase name-like tokens, or partial reanalyses.

Use a mixture:
- Homophonous/alternate spelling: Jordan Lee → Jordan Leigh; Alvarez → Alvares; Selina → Selena; Cortes ↔ Cortez.
- Surname substitution: Carlisle → Carlyle; Aldridge → Aldrich; Trombley → Trembly.
- Rough phonetic/lowercase output: Eckhart → hackhart; Kestrel → kestrel-like or a word fragment if drawn erroneous.
- Name-to-word decoding: Lois → Lowest; Wesley Trombley → Wesley family; “It’s Wesley Trombley” → “It was Lee Trombley.”
- Component loss or split: Nadine Carlisle → Nadine; Maria Alvarez → Share Maria Alvarez if the initial “Sure” is absorbed.
- Familiar first names can vary too; do not reserve all name errors for rare surnames.

Names embedded in emails, organizations, product/account phrases, or longer sentences are still decoded from sound. Explicit spelling helps but is not perfect. Prior context must not force consistency: a repeated name can become correct, stay wrong, or change to a different wrong form.

NUMBERS AND DIGITS

Preserve short and medium numeric material. When a drawn minor or substantial outcome lands on a turn with no name and no identifier of ten or more digits, put the error on an ordinary word, never on a short number, date, ZIP or card ending.

General:
- 3–5 digit strings, ZIPs, short card endings, dates, prices, and ordinary times are highly reliable.
- 6–9 digit IDs are also usually preserved.
- Ten or more digits are the main failure zone: roughly one in four long identifiers fails to preserve every digit.
- Do not damage a ZIP, a card ending, and a phone number all in the same turn unless the draw is substantial and the whole identifier region is unstable.
- Do not validate, pad, repair, or complete malformed numbers from context.

Long-number failures:
- Substituted digit: 541-555-0188 → 541-555-0183.
- Lost digit: 212-555-0133 → 212-555-013.
- Repeated/collapsed run: 4111 1111 1111 4417 → 411111114417.
- Overlap/restart: 706-555-0173 → 706-505-173-0173.
- Letter/digit confusion: card ending 1156 → card ending E1556.
- Streaming partials: My phone is 541 || five, five, five, zero || One || 3, 3.

Short-number handling:
- ZIP 97330 usually remains 97330.
- Card ending 4417 usually remains 4417.
- A 5-digit ZIP can occasionally be rendered with a hyphen or spacing while preserving digits: 9-7330.
- A short field may rarely have one local mistake, but this should not be the default minor-error target.

Numeral rate:
- Only about 35% of turns contain numerals. Avoid automatic numeral conversion in every possible place.
- Spoken digit strings may sometimes remain as number words, especially inside streaming, uncertainty, or partial decodes.
- Digit-by-digit number-word sequences are rare but real, about 1% of turns:
  - “five four one five five five zero one eight eight”
  - “one one five six”
- Do not use number words so often that numeric identifiers stop looking like ASR. Most ZIPs, dates, times, prices, phone numbers, and card endings still normalize to digits when clean.
- Do not invent unrelated numbers. Lower numeral rate by leaving some spoken numbers speech-like or by losing/clipping numeric material when the draw calls for it, not by suppressing important recognized digits.

Common numeric formatting habits:
- Phone numbers often hyphenate: 541-555-0188.
- 16-digit card numbers often collapse into one continuous string rather than preserving source grouping: 4111111111114417.
- Card endings are usually compact digits: card ending 4417.
- ZIPs generally use digits.
- Dates often become “August 14th,” “April 12th, 1990,” or “June 30th, 1972.”
- Weekday + date often receives a comma: “Monday, August 10th.”
- Times usually become “8 a.m. to 12 p.m.” Lowercase punctuated a.m./p.m. is more typical than “8 AM to 12 PM.”
- Prices usually use currency notation: $85.
- Contextual ordinals can become numerals: “the eighteenth” → “the 18th,” but not every ordinal must normalize if the draw or local style is speech-like.

STREAMING SPLITS

Multiple recognition segments occur on 6.2% of all turns, including lexically correct turns. Because absent turns cannot split, this is about 6.4% of captured turns.

If the split draw says split, visibly keep separate segments. Do not concatenate during cleanup.

Favor boundaries:
- After “Hi,” “Yes,” “OK,” “Okay,” “Thanks,” “Understood,” or “Sure.”
- Between a name and callback/demographic information.
- Between short form fields: ZIP || card ending.
- Inside slowly spoken phone numbers or long identifiers.
- Before an appended request or after a completed sentence.
- In repeated/repair-like recognitions.

Examples:
- Hi. || I’m calling to schedule my son’s next allergy shot.
- Jordan Lee || my phone number is 541-555-0188.
- ZIP 97035 || Kard-ending 1156.
- That’s all I needed. || Thank you.
- My phone is 541 || five, five, five, zero || one || three, three.

Segments can have local formatting:
- One segment may end with punctuation and the next begin lowercase.
- One segment can use digits while another uses words.
- A segment may be a single word or digit.
- Later segments may overlap or restart earlier material.

TERMINAL PUNCTUATION AND CASING

No terminal punctuation occurs on 9% of turns. Use it especially for:
- Name + phone fragments.
- ZIP/card fragments.
- Short confirmations.
- Clipped fragments.
- Repeated closing fragments.
- Numeric endings.

But do not remove terminal punctuation from every contact fragment; many have a period.

Entirely lowercase occurs on 1.7% of turns. This means the whole transcript is lowercase, not merely “zip.” Use sparingly.

Casing habits:
- “Zip” is common, especially at the start of compact verification fragments. “ZIP” also occurs, but do not copy all-caps from the source by default.
  - Common: “Zip 97330, card ending 4417.”
  - Also valid: “ZIP 97330, card ending 4417.”
  - In prose: “my zip code is 34786.”
- “OK” and “Okay” both occur; short standalone acknowledgments readily become “OK.”
- Product, plan, and brand names are often recognized correctly, but capitalization can be semantic or inconsistent:
  - “upgrade me to total” can occur.
  - Familiar brands like Medicare, Botox, CareCredit, Apex Credit Union are usually intact, but not guaranteed.
- Unfamiliar name-like errors may be lowercase: “hackhart file.”
- Do not preserve source capitalization merely because it is visible.

PUNCTUATION STYLE

Automatic punctuation is local and sometimes unlike the source.

Common habits:
- Comma rather than period between a name and a following demographic phrase:
  - “Dana Whitlock, my phone number is 541-555-0188.”
  - “Jordan Lee, my date of birth is April 12th, 1990.”
- Colon sometimes after structured labels:
  - “date of birth: September 8th, 1995.”
- Weekday-date comma:
  - “Sunday, August 9th.”
  - “Monday, August 10th, 8 a.m. to 12 p.m.”
- Optional comma before “and” is often absent:
  - “back and when someone might call me”
  - “Botox and whether you offer CareCredit”
- Separate source sentences may become comma-linked:
  - “That’s all I needed, thank you.”
- Declarative or indirect requests can receive a question mark:
  - “I was wondering if Botox can be discussed during that same visit?”
  - “In California?”
- Warm farewells can receive an exclamation mark, but not often.
- Some fragments end with a comma.
- Do not overfit punctuation to the caller text.

ORDINARY-WORD ERRORS

Include ordinary acoustic errors often enough that identifiers are not the only damaged material.

Good minor examples:
- Sure → Share
- want to → wanna
- booking → book in
- leave a message → leave the message
- just to note → just a note
- opened → open
- had → have
- move to → move too
- drop an unstressed “Uh,” “I,” “the,” or “a”

These should look like recognition, not paraphrase. Preserve awkward recognized wording. Do not improve grammar or make the utterance more semantically helpful.

SUBSTANTIAL ERROR STYLE

Substantial errors are localized but obvious. Use them especially for difficult names, account/product names, phone/card/order identifiers, and context-poor short utterances.

Examples:
- “What’s the status on my Eckhart file?” → “What’s the status on my hackhart file?”
- “It’s Wesley Trombley.” → “It was Lee Trombley.”
- “Selina Cortez, 541-555-0171.” → “Selina Cortes || King George se qwarta jun, King George ikkewell tis-sinq.”
- “ZIP 97035, card ending 1156.” → “ZIP 97035, card ending E1556.”
- “Yes, Monday August tenth, 8am to 12pm.” → “Yes, Monday, August 10th, 8 a.m. to 12 p.m.” if correct; if substantial, damage one time or identifier region, not the whole sentence.

Rare multilingual/phonetic fragments are allowed, usually in digit/name regions. Do not make them the normal mechanism. Do not translate full English sentences.

REPETITION AND CONTEXT

Context helps but does not create a correction dictionary.

Repeated turns can:
- Transcribe identically.
- Disappear if the draw is absent.
- Clip the beginning.
- Change punctuation only.
- Correct a prior error.
- Repeat the same error.
- Acquire a different error.

Do not force consistency of names, product capitalization, ZIP casing, card formatting, or phone-number rendering across turns. Do not use an earlier correct value to repair a current malformed recognition.

NOISE AND CONNECTION LABELS

“Perfect” connection does not guarantee perfect recognition. Errors, drops, clipping, and streaming occur on perfect calls.

Background noise or bad signal weakly increases capture and decoding risk, but does not require every utterance to be damaged. Many noisy turns transcribe completely correctly.

FINAL CHECK BEFORE EMITTING

Check the drawn class and the recognizer’s measured habits, not readability.

- If absent, output no transcription.
- If clipped, remove a real edge span.
- If minor/substantial, make an actual lexical/token change, not only punctuation.
- If correct, do not add an extra lexical error for flavor.
- If split, preserve visible segment boundaries.
- If no-terminal was drawn, omit final punctuation.
- If the turn contains a name, ask whether visible spelling has improperly rescued it.
- If the turn contains digits, ask whether you over-damaged short fields or under-damaged a drawn long-identifier failure.
- If numerals appear, ask whether they are natural ASR normalization rather than automatic conversion of every spoken number.
- Do not repair malformed identifiers, odd casing, or rough phonetic tokens during cleanup.