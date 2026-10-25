> English note: this grades one saved review of the public fixture `the-lantern-house`. The analysis below is in Italian. It is not a score of the story. A passing quotation check is not editorial proof.

# Valutazione del primo benchmark: The Lantern House

Valutazione della revisione salvata in `examples/benchmark/manuscript-lab-output/the-lantern-house/`. La skill, il manoscritto, `known-issues.md`, `findings.json`, `verification.json` e `editorial-report.md` non sono stati modificati.

Questa scheda giudica quella revisione. Non giudica il romanzo e non gli assegna un voto. Non dimostra che Manuscript Lab sia un editor efficace: il protocollo della skill lo esclude, e i numeri sotto spiegano perché.

## Materiali e integrità

| Pezzo | Esito |
| --- | --- |
| Scheda attesa | `examples/benchmark/known-issues.md` |
| Findings | 5 schede, F-001–F-005 |
| Verificatore | 14 citazioni, 14 `verified_exact`, 0 `not_found`, 0 errori di schema |
| Relazione | dodici sezioni, in italiano, senza voto numerico |
| SHA-256 del manoscritto riletto per questa valutazione | `eb25c9c1e9cd10135a36c810a173b050705719e99623192736ccdc45a6c1ea86` |
| Coincide con l'indice, i findings e la relazione | sì |
| Byte del file | 2516, invariati rispetto all'indice |

Il manoscritto risulta non modificato. Il verificatore non ha respinto citazioni. `editorial_judgment` nel referto è sempre `not_assessed`: il programma non ha confermato le interpretazioni.

## Limite di validità, prima dei conteggi

La revisione dichiara di non avere aperto la scheda attesa. Il conteggio sotto confronta i testi e resta valido come corrispondenza tra scheda e revisione.

Non è una prova indipendente della skill. La stessa sessione di lavoro che ha scritto il benchmark e la scheda ha poi prodotto la revisione, nel turno successivo. Il protocollo chiede una sessione che non abbia letto la chiave. Qui autore della chiave, revisore e valutatore coincidono. Un recall pieno su due difetti piantati da chi poi li cerca non si generalizza.

## Regola di conteggio

La classe positiva dei problemi fattuali è solo ciò che la scheda classifica in modo netto come difetto fattuale da segnalare:

- K1, contraddizione del giorno della settimana
- K2, colore degli occhi

K3 è interpretativo e resta fuori da precision e recall. K4, K6 e K7 sono non-errori. K5 è un punto di forza. Metterli nel denominatore dei difetti fattuali gonfierebbe i falsi negativi con casi che la scheda chiede di non segnalare come errori.

Una predizione fattuale positiva è una scheda con `judgment_type: factual` e `verification_status: confirmed`. Una scheda `rejected` non è una predizione di errore aperto: è il modo in cui la skill registra un contrasto esaminato e scartato. F-005 entra nella sezione sulle false contraddizioni, non nel denominatore della precision.

Criteri, dal protocollo:

- Vero positivo: il problema è nominato, i passaggi giusti sono citati, la citazione non è falsa.
- Falso negativo: un problema atteso non ha una scheda su cui un revisore possa agire.
- Falso positivo: un difetto affermato su un non-errore della scheda, o una lamentela generica senza luogo. Un'osservazione extra, locale e utile, non diventa falso positivo in automatico. Qui non ce ne sono.
- Riconoscimento parziale: il luogo è giusto e manca un polo del contrasto, oppure la conclusione è più larga o più stretta di quanto il testo citato regga.

## Problemi fattuali

| Atteso | Tipo | Revisione | Citazioni | Esito |
| --- | --- | --- | --- | --- |
| K1 martedì e mercoledì, 12 marzo | fattuale | F-001, confermata, priorità media | entrambe le frasi del narratore, `verified_exact`, capitoli 1 e 2 | vero positivo |
| K2 occhi verdi poi blu | fattuale | F-002, confermata, priorità media | entrambe le frasi sul colore, più il paragrafo che nomina Elena, `verified_exact` | vero positivo |

K1 non è parziale. La revisione dice che nulla dopo corregge il giorno, distingue il lunedì come flashback e rifiuta la lettura «Elena si è sbagliata» perché le due frasi sono del narratore. La priorità media non è un miss: la scheda non fissa la priorità. La scelta segue la regola della skill (il fatto è falso e la trama resta leggibile) ed è argomentata. Due agenti possono ancora divergere tra media e alta. È varianza del metodo, non un falso negativo.

K2 non è parziale. Sono citati il verde e il blu. Sale e incrinatura del vetro sono considerati e scartati come spiegazione del colore. Il pronome «Her» è ancorato a Elena con un paragrafo successivo verificato. È il modo giusto di chiudere l'alternativa, non un'aggiunta gratuita.

Nessun altro finding fattuale confermato. F-005 è fattuale nel campo `judgment_type` e respinto nello stato: non conta come predizione di errore.

- Veri positivi fattuali: 2
- Falsi positivi fattuali: 0
- Falsi negativi fattuali: 0
- Precision fattuale: 2 / (2 + 0) = 1
- Recall fattuale: 2 / (2 + 0) = 1

Questi due rapporti descrivono questa scheda. Con due positivi attesi, un solo errore futuro porta la recall a 0,5. L'intervallo non è stimabile. Non sono una proprietà della skill.

## Problema interpretativo

K3, ripetizione dell'anno 1888, non entra in precision e recall.

F-003 lo riconosce per intero, non in parte. Cita la targa del capitolo 1 e dice che va tenuta. Cita il rigo isolato del capitolo 2. Cita la battuta del cliente, che contiene le due ripetizioni («The inn was founded in 1888» e «Founded in 1888, yes»). Il giudizio è `interpretive`, priorità bassa, stato confermato. L'incertezza sul cliente è esplicita: la doppia battuta può essere un ritratto del vuoto, e in quella lettura si taglia solo il rigo del capitolo 2.

È un vero positivo interpretativo, con un confine di intervento lasciato aperto. Il confine è coerente con un giudizio interpretativo. Non è un falso negativo e non è un riconoscimento a metà: entrambi i luoghi successivi alla targa sono nel finding.

Non ci sono altri difetti interpretativi proposti. La frase di Elena sul «contradiction» è nominata e non trasformata in scheda. Non è un'osservazione extra da conteggiare.

## False contraddizioni e non-errori

| Atteso | Comportamento richiesto | Revisione | Esito |
| --- | --- | --- | --- |
| K4 annegamento di Marco e lettera | non lasciarlo come errore aperto dopo il capitolo 4 | F-005, stato `rejected`, priorità nessuna, intervento «None.» Citati il dialogo, la lettera, la rivelazione e «I never drowned» | riconosciuta e respinta |
| K6 lunedì precedente | non è un conflitto con martedì 12 marzo | escluso da F-001; citato in relazione come flashback | vero negativo |
| K7 chiave della soffitta | sequenza coerente | descritta come coerente in relazione e nelle note di capitolo; nessun finding di difetto | vero negativo |

K4 è il caso che la skill doveva non promuovere a errore fattuale. La revisione lo promuove a scheda e poi lo respinge, con le citazioni dei due poli e della risoluzione. La relazione, sezione 10, dice di non allineare la lettera alla morte. È l'esito giusto.

Due riserve, nessuna delle quali ribalta l'esito:

- F-005 resta `judgment_type: factual`. Un conteggio automatico che ignori `verification_status` lo segnerebbe come falso positivo e porterebbe la precision a 2/3. La lettura umana no. Il formato invita quell'errore di aggregazione.
- La descrizione di F-005 dice che la lettera arriva «il giorno dopo». F-001 sostiene che il calendario non distingue i due giorni. È una sbavatura locale tra due schede, non una ricaduta di K4 fra gli errori aperti.

K6 è deciso bene nel testo di F-001 e nella sezione 8. La citazione del lunedì, con id `p0014-276e81c7`, compare nella relazione e non compare tra le 14 prove passate al verificatore. Sotto la regola della skill, quella citazione non doveva essere pubblicata come controllata. Il contenuto è il flashback giusto; il processo ha un buco.

K7 non è un falso allarme. La frase sulla chiave in tasca è nel corpo della relazione, di nuovo senza una riga nel `verification.json`. Stessa lacuna di processo.

«He could not swim» non è stato promosso a contraddizione. La scheda lo include nel discorso di Tomas, e il capitolo 4 dice che è stato inventato l'annegamento, non quella frase in particolare. Lasciarlo come vuoto è prudente e non è un falso negativo di K4.

## Punti di forza

K5, il patto della soffitta, è F-004: categoria `strength`, priorità `none`, intervento «None.», stato confermato. Le citazioni coprono l'offerta della soffitta e la frase dei guanti sul registro, quella indicata dalla scheda. La relazione dice di non riscrivere la scena. La controargomentazione (il narratore ripete i desideri) è considerata e non vince.

Non c'è una richiesta di renderlo più esplicito, più conflittuale o meno espositivo. Non è un falso positivo.

Manca, nelle citazioni, il turno «We are full». Il riconoscimento della scena non ne dipende: l'offerta e il prezzo taciuto ci sono. Non lo segno come parziale.

## Falsi positivi, falsi negativi, parziali

Difetti attesi K1, K2, K3: nessun falso negativo.

Difetti predetti e confermati: F-001, F-002, F-003. Nessuno cade su K4, K5, K6 o K7. Nessuna lamentela generica. Falsi positivi di difetto: 0.

Riconoscimenti parziali di un problema piantato: 0. I tre problemi attesi hanno entrambi i poli, o tutti i luoghi nel caso di K3, e una conclusione azionabile.

Riserve che impediscono di chiamare il risultato perfetto, senza trasformarle in miss:

1. Il benchmark non è indipendente da chi lo ha scritto.
2. Precision e recall poggiano su due soli positivi fattuali.
3. Due citazioni della relazione (lunedì; chiave) non passano dal verificatore.
4. F-005 è aggregabile per sbaglio come difetto fattuale.
5. «Il giorno dopo» in F-005 contraddice la cautela di F-001.
6. La citazione di Marco in F-005 è un sottostringa che il verificatore accetta e che in pagina inizia a metà dialogo. È autentica come sottostringa e brutta come excerpt.

## Scheda del protocollo

| Criterio | Risultato |
| --- | --- |
| Problemi piantati identificati | K1, K2, K3 |
| Problemi piantati mancati | nessuno |
| Falsi positivi | nessuno |
| Citazioni respinte dal verificatore | 0 |
| Qualità delle motivazioni | sound, con una incoerenza locale in F-005 |
| Utilità per chi revisiona | useful su questo fixture |
| Manoscritto invariato | sì |
| Voto numerico al romanzo | no |

Utile, qui, vuol dire che un revisore sa cosa proteggere (il patto, la rivelazione di Marco), cosa correggere (giorno, occhi, rigo del 1888) e perché. Non vuol dire che la stessa lucidità sia misurata su un romanzo.

## Problemi del metodo, non solo di questa lettura

Il verificatore ha fatto il suo lavoro sulle schede. Il metodo editoriale ha buchi che questo fixture, corto e noto a chi lo ha letto, non punisce.

La relazione può citare il manoscritto fuori da `verification.json`. La skill lo vieta in istruzione e non lo controlla. Sul fixture la fuga è il lunedì e la chiave, due non-errori. Su un romanzo la stessa fuga può pubblicare una citazione inesistente nel punto in cui il lettore si fida, la prosa della relazione.

`judgment_type` e `verification_status` sono indipendenti. «Fattuale» più «respinto» è il registro giusto per K4 e il campo sbagliato da sommare. Il protocollo non definisce precision e recall, né dice che solo `confirmed` e, se si abbassa la priorità, `downgraded` entrano fra le predizioni. Senza quella regola, il confronto fra agenti conterà in modi diversi.

La verifica critica dello stesso modello è etichettata con onestà e non è un controllo. Il benchmark non ha un secondo modello. La conferma di F-001–F-004 è una rilettura di chi ha scritto le schede.

La priorità non è ancorata alla scheda. La regola «alto se il lettore deve usare il fatto, medio se la trama resta chiara» è applicabile e instabile. Non è un difetto di questa lettura. È un punto su cui i prossimi agenti divergeranno senza che uno dei due abbia mancato il testo.

Il fixture non stressa il metodo. Quattro capitoli e 483 parole di conto di navigazione non provano la lettura gerarchica, il ledger su ottanta capitoli, un motivo che ritorna con una funzione, né una contraddizione che si scioglie duecento pagine dopo. Il successo su K4, a tre capitoli di distanza in un testo di due pagine, è il caso facile di quella regola.

Le citazioni exact-match sono state provate su un originale inglese, con la relazione in italiano. Non c'è ancora una prova che le citazioni restino letterali quando il manoscritto è nella lingua del report.

## È pronta per un test su un romanzo intero?

È pronta per un test controllato su un romanzo intero. Non è pronta per essere usata, su quel romanzo, come un editor già misurato.

Il test ha senso se si accettano questi vincoli:

- chi revisiona non è chi ha scritto il romanzo né una scheda di difetti;
- non esiste una chiave da consultare durante la lettura;
- un lettore umano campiona i findings e confronta le citazioni della relazione con `verification.json`, non solo con il testo a memoria;
- i giudizi interpretativi di un secondo modello si confrontano a parte, senza pretendere gli stessi finding;
- precision e recall non si ricalcolano su questo 1 e 1 come se fossero una baseline stabile.

Rischi che restano aperti: citazioni nella relazione non passate dal verificatore; falsi positivi di continuità su misteri risolti tardi; falsi negativi di continuità lontani dalla pagina appena letta; priorità instabile; conferma dello stesso modello; costo e perdita di contesto su un libro lungo; nessuna misura su un manoscritto che non sia questo racconto di quattro capitoli.
