# Machine Learning – Groep G09

## Analyses per student

| Student | Reeks | Analyse | Onderwerp |
| --- | --- | --- | --- |
| Arne Bogaert | Reeks 1 | Analyse 1 | Anomaliedetectie op fietstellingen |
| Arne Bogaert | Reeks 2 | Analyse 1 | Tijdreeksvoorspelling van fietstellingen |
| Evy Coulier | Reeks 1 | Analyse 3 | Clustering van Blue-Bike stations |
| Evy Coulier | Reeks 2 | Analyse 3 | Tijdreeksvoorspelling van Blue-Bike uitleningen |
| Luiz Verheyen | Reeks 1 | Analyse 2 | Maandclassificatie op basis van weerdata |
| Luiz Verheyen | Reeks 2 | Analyse 2 | Temperatuurvoorspelling per meetstation |

De analyses staan in `analyses/ML_Analyses_<naam>.ipynb`.

---

## Modellen lokaal trainen

De getrainde modellen staan **niet in git** (te groot). Je moet ze eenmalig lokaal aanmaken via de trainscripts in de map `trainingscripts_models/`.

```bash
cd trainingscripts_models
python train_models.py     # weermodellen → models/weer/
python train_fietsers.py   # fietstellingsmodellen → models/fietsers/
python train_bluebike.py   # Blue-Bike modellen → models/bluebike/
```

> Vereiste: de DWH-verbinding moet actief zijn. Zorg dat `.env` correct is ingesteld.

---

## Dashboard uitvoeren

```bash
cd group
streamlit run app.py
```

### Wat doet het dashboard?

Het dashboard laat toe om via spraak of tekst een voorspellingsvraag te stellen over:

- **Weer** – gemiddelde temperatuur voor 1 tot 7 dagen vooruit, per weerstation
- **Fietsers** – verwacht aantal fietsers per dag, per telpaal
- **Blue-Bikes** – verwacht aantal uitgeleende fietsen per dag, per station

Een LLM (Llama 3.3 via Groq) analyseert de vraag en bepaalt het onderwerp, de locatie en het aantal dagen. De bijhorende `.pkl` modellen worden geladen en de voorspellingen worden getoond als tabel en grafiek. Als de locatie niet automatisch herkend wordt, kan je ze manueel selecteren.

> Vereiste: `GROQ_API_KEY` instellen in `.env`.
