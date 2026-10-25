> English note: this grades one saved review of the public fixture `the-mile-road`. The analysis below is in Italian. It is not a score of the story. A passing quotation check is not editorial proof.

# Valutazione del benchmark a lunga distanza: The Mile Road

Confronto fra la revisione cieca di Codex e `evaluations/keys/the-mile-road-known-issues.md`.

Non sono stati modificati la skill, il manoscritto, la chiave né i file di Codex. Quattro copie locali (`findings.json`, `editorial-report.md`, `continuity-ledger.md`, `technical-checks.json`) hanno lo stesso SHA-256 dei file nella cartella di output di Codex. Il giudizio usa quella cartella, perché lì stanno anche `verification.json`, `report-check.json` e `score.json`.

Questa scheda non dà un voto al racconto. Precision e recall descrivono questa revisione su cinque difetti fattuali. Non dimostrano che Manuscript Lab regga un romanzo diverso.

## Regola di conteggio

Problemi fattuali con classificazione attesa chiara: L1, L2, L3, L4, L5.

Una predizione positiva è un finding con `nature: factual` e `editorial_status: confirmed`. È la regola di `score.json`. I finding respinti non entrano nel denominatore, anche se la natura è fattuale.

Un vero positivo richiede i poli del contrasto, i capitoli della chiave e citazioni che contengono gli excerpt attesi. Il titolo non basta.

L6 è una falsa contraddizione da non lasciare aperta. L7 e L8 non vanno puniti. L9 non va riscritto; registrarlo come forza è appropriato, non obbligatorio per il conteggio fattuale.

## Corrispondenza

| Chiave | Tipo | Finding | Stato | Capitoli citati | Poli della chiave nelle prove | Esito |
| --- | --- | --- | --- | --- | --- | --- |
| L1 giorno della piena | fattuale | F-001 | confirmed | c001, c017 | venerdì 2 maggio e giovedì 2 maggio, entrambi del narratore | vero positivo |
| L2 lato della cicatrice | fattuale | F-002 | confirmed | c002, c015 | guancia sinistra e guancia destra, lo stesso segno | vero positivo |
| L3 tazza blu | fattuale | F-003 | confirmed | c004, c006, c016 | abbandono, inventario negativo, tazza portata dalla chiesa | vero positivo |
| L4 età | fattuale | F-005 | confirmed | c003, c011, c018 | diciannove anni, diciannove giorni senza compleanno, ventisei alla partenza | vero positivo |
| L5 ponte e Osip | fattuale | F-004 | confirmed | c010, c012, c013, c016 | nessuno glielo ha detto; Osip assente dal fiume; «Osip told me yesterday» | vero positivo |
| L6 lettera di Tomas | risolta | F-006 | rejected | c005, c008, c014 | morte, firma, figlio vivo, nome dello zio | non lasciata aperta |
| L7 pozzo di agosto | flashback | F-007 | rejected | c001, c007 | anni prima; «That August was not this May» | non punito |
| L8 mantello grigio | coerente | nessuno | — | c009, c013, c018 nel ledger e nella relazione | consegna, uso, chiodo | non punito |
| L9 patto del traghetto | forza | nessuno | — | c010, solo come nota | l'ancora del registro è nel capitolo, non in un finding | non punito; forza non registrata |

Nessuna delle cinque conferme è solo omonimia di titolo. Ogni prova `verified_exact` contiene l'excerpt della chiave, spesso dentro una citazione più lunga che include la frase successiva. I capitoli sono quelli attesi. L4 è F-005 e L5 è F-004: l'ordine degli id non segue la chiave, il contenuto sì.

## Metriche fattuali

- Veri positivi: 5 (L1–L5)
- Falsi positivi: 0
- Falsi negativi: 0
- Precision: 5 / (5 + 0) = 1
- Recall: 5 / (5 + 0) = 1

`score.json` elenca le stesse cinque predizioni positive, F-001–F-005, ed esclude F-006, F-007 e F-008 come respinti. Quel file non confronta la chiave. La corrispondenza con L1–L5 è un giudizio editoriale di questa valutazione, non un output dello script.

Con cinque positivi, un solo miss futuro porterebbe la recall a 0,8. Il rapporto descrive questo foglio.

## False contraddizioni e non-errori

L6 è il caso che il benchmark doveva non promuovere a errore aperto. F-006 lo formula come ipotesi e lo respinge dopo il capitolo 14. Le prove coprono il ghiaccio di gennaio, la firma dal porto, «The letter was from my son» e «He signed his dead uncle's name». Priorità `none`, intervento di non correzione. Il narratore tiene in vita il figlio e lascia morto il fratello. Esito corretto, non parziale.

L7 è respinto con i due segnali temporali della chiave. Non diventa un secondo calendario della piena.

L8 non ha un finding. Il ledger e la sezione 2 della relazione seguono il mantello da Osip al chiodo e lo dichiarano compatibile. Nessuna correzione. Esito corretto.

L9 è parziale rispetto al suggerimento positivo della chiave, e completo rispetto al divieto di riscriverlo. Il capitolo 10 nota che la barca «piena» ammette il pavimento e che la firma non narrata è una lacuna, non una contraddizione. Nessun intervento chiede di rifare la scena. La sezione dei punti di forza nomina Tomas, il pozzo e il mantello, non il patto. La chiave dice che registrarlo come forza è appropriato. Codex non lo ha fatto. Non è un falso positivo.

F-008 non è nella chiave. È un'ipotesi respinta: il capitolo 11 anticipa i diciannove giorni e il capitolo 12 torna al nono giorno. Lo stato è `rejected`, la priorità è `none`, l'intervento è nessuno. Non conta come falso positivo di difetto. È un non-errore in più, esaminato e scartato. Le stesse frasi sui diciannove giorni servono anche a F-005 come vincolo di età. Sono due domande, non un difetto duplicato.

## Omissioni, duplicazioni, classificazioni

Non manca nessuno dei cinque difetti fattuali. Ogni polo è citato. Non c'è un sesto finding confermato.

F-004 dice esplicitamente che la notizia nascosta e l'incontro con Osip sono una sola catena, non due errori. La chiave li tiene insieme in L5. Nessuna duplicazione.

Le cinque conferme sono `factual` e `continuity`. L'età non è ridotta a una bugia di Lev: il finding cita anche «Mara was nineteen» del narratore. Il giovedì del capitolo 17 non è trattato come un ricordo incerto di Lev: la prova include la frase che presenta il resoconto come conto del capitolo. Classificazione aderente al testo.

L'incertezza di F-004 è moderata, perché una battuta può essere falsa. Il finding resta confermato e dice che il testo non sostiene né risolve quella menzogna. Non è un riconoscimento a metà: i tre excerpt di L5 ci sono. È una riserva esplicita, più stretta di un semplice «contraddizione chiusa».

Nessun finding è `downgraded`. Nessun finding interpretativo è stato presentato come fatto, e nessuna forza è stata messa fra le predizioni positive.

## Controlli tecnici e giudizio editoriale

Lo SHA-256 del manoscritto nel repository, riletto per questa valutazione, è `2651e9aa461086b7ab3f8689b4c7e026aa9a667f37890015db806a035169443b`. Coincide con `findings.json`, `verification.json`, la relazione e `technical-checks.json`, che segna il file invariato prima e dopo la revisione.

| Controllo | Esito nei file di Codex | Che cosa non dimostra |
| --- | --- | --- |
| `verify_evidence.py`, exit 0 | 8 finding, 32 citazioni, 32 `verified_exact`, zero `not_found`, zero errori di schema o semantici del record. `editorial_judgment` è `not_assessed` su ogni riga. Nessun `mid_token` o `inside_quotation`. | Non conferma che il contrasto sia un difetto. |
| `check_report.py`, exit 0 | 32 citazioni di blocco, zero errori, zero avvisi. `semantic_correctness` è `not_assessed`. | Non legge se la prosa italiana ha capito il libro. |
| `score_findings.py`, exit 0 | Predizioni positive: F-001–F-005. Esclusi i tre respinti. | Non confronta la chiave e non è un voto del romanzo. |
| Schema | `technical-checks.json` dice che il pacchetto `jsonschema` non c'era e che lo schema è stato controllato da `verify_evidence.py`. Quel controllo, nel referto, è vuoto di errori. | È il validatore interno della skill, non un certificatore esterno. |

`technical-checks.json` ha `passed: true`. Quel flag riassume i comandi e la copertura. Non è il giudizio su L1–L9. La corrispondenza con la chiave è fatta qui, a mano, sulle citazioni.

La relazione ha dodici sezioni e una nota per ciascuno dei 18 capitoli. Il conteggio di navigazione dichiarato è 1.225 parole. La modalità è `continuity` / `deep`: stile e ritmo sono dichiarati fuori ambito. Questo limita L9, non i cinque fatti.

## Limiti del benchmark

Il fixture è stato scritto da un agente AI nello stesso progetto della skill. Codex dichiara di non avere aperto la chiave (`keys_consulted: false` nel riepilogo tecnico, e la stessa frase nella relazione). Non ho un modo indipendente per ispezionare il contesto di quella sessione. La chiave non sta nella cartella del manoscritto. Questo riduce la contaminazione rispetto a una revisione fatta da chi ha piantato i difetti. Non la elimina come rischio di disegno: il testo stesso segnala parecchi impianti.

Esempi nel manoscritto, non nella chiave soltanto:

- la cicatrice: «She did not say that the scar had moved»
- il giovedì: «nothing later took it back»
- l'età: «The number of her years had changed without the book showing the change»
- la lettera: «Mara did not yet know which Tomas the fire had eaten»
- il pozzo: «That August was not this May»

Le distanze ci sono: capitoli 1 e 17, 2 e 15, 4 e 16, 3 e 18, 12 e 16. Un lettore deve comunque tenere i due poli. Il libro, però, glieli indica. Una recall di 1 su questo foglio è meno informativa di una recall di 1 su contraddizioni che il testo non commenta.

F-008 mostra che Codex ha anche scartato un sospetto non piantato. È un buon segno di contenimento, su un solo caso, in un testo di diciotto capitoli brevi. Non misura i falsi allarmi su un romanzo lungo che non annuncia i propri errori.

## Conclusione

Su L1–L5 la revisione è completa, non parziale: cinque veri positivi, nessun falso positivo confermato, nessun falso negativo fattuale. Precision e recall, con la regola dei soli fattuali confermati, sono 1 e 1.

L6 è riconosciuta e chiusa. L7 e L8 non sono puniti. L9 non è riscritto e non è registrato come punto di forza: è l'unico scarto rispetto al suggerimento della chiave, ed è parziale solo su quel suggerimento.

Il risultato tecnico degli script è pulito e va tenuto distinto da questo giudizio. Il risultato editoriale, su questo fixture, è alto. Non va letto come prova che la skill abbia superato la continuità a lunga distanza in un romanzo che non segnala da sé le incongruenze, né come una misura indipendente dal fatto che il benchmark è stato generato da un agente.
