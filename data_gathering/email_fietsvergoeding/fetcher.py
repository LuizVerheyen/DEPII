"""
Fetcher voor fietsvergoeding-emails.

Haalt nieuwe e-mails op uit Gmail (via simpleGmail), append ze aan
``emails.csv``, en verwerkt nieuwe (nog niet verwerkte) e-mails via een LLM
(Groq) tot gestructureerde rijen die aan ``emails_final.csv`` worden geappend.

Gebruik
-------
Roep :func:`fetch_and_process` aan voordat ``fillDimStaff`` of
``fillFactStaffCommute`` worden uitgevoerd. ``filler._load_combined()`` doet
dit automatisch (één keer per process).

Tracking
--------
``emails_final.csv`` krijgt een ``EmailId``-kolom (eerste kolom) zodat we
kunnen tracken welke e-mails al verwerkt zijn. Bestaande rijen zonder
``EmailId`` (legacy data) worden bij de eerste run mogelijks opnieuw verwerkt;
duplicaten worden gededupliceerd op ``(StaffID, Period, DistanceKM)``.

Disable
-------
Zet ``SKIP_EMAIL_FETCH=1`` in de omgeving om de Gmail/LLM-stap volledig over
te slaan (handig voor unit tests en CI).
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[2]
EMAIL_DIR = ROOT / "data" / "e-mails_fietsvergoeding"
EMAILS_CSV = EMAIL_DIR / "emails.csv"
EMAILS_FINAL_CSV = EMAIL_DIR / "emails_final.csv"

EMAILS_RAW_COLUMNS = ["Id", "DateKey", "TimeKey", "From", "Subject", "Message"]
EMAILS_FINAL_COLUMNS = (
    ["EmailId", "StaffID", "Entity", "Campus", "PostalCode", "DistanceKM", "Period"]
    + [f"dag {i}" for i in range(1, 32)]
)

ALLOWED_SENDER = "Sabine De Vreese <sabine.devreese@hogent.be>"

# Locale-onafhankelijke maand-afkortingen (consistent met fietsvergoedingen-CSV)
_MONTH_SHORT = {
    1: "jan", 2: "feb", 3: "mrt", 4: "apr", 5: "mei", 6: "jun",
    7: "jul", 8: "aug", 9: "sep", 10: "okt", 11: "nov", 12: "dec",
}

# Module-level cache voor LLM-instantie (lazy-init)
_llm = None


# ── Stap 1: Gmail-fetch ──────────────────────────────────────────────────────

def _fetch_new_gmail_messages() -> int:
    """
    Haalt nieuwe Gmail-berichten op (subject 'Aanvraag fietsvergoeding') van de
    afgelopen 7 dagen en append rijen die nog niet in emails.csv staan.

    Returns het aantal nieuw toegevoegde e-mails. Bij netwerk- of auth-fouten
    wordt 0 teruggegeven (en een warning gelogd) zodat de pipeline doorloopt.
    """
    try:
        from simplegmail import Gmail
    except Exception as e:
        logger.warning("simpleGmail kon niet geïmporteerd worden: %s — Gmail-fetch overgeslagen", e)
        return 0
    
    
    try:
        gmail = Gmail()
    except Exception as e:
            logger.warning("Kan niet authenticeren bij Gmail: %s — fetch overgeslagen", e)
            return 0

    query_params = {
        "newer_than": (7, "day"),
        "query": 'subject:"Aanvraag fietsvergoeding"',
    }

    try:
        messages = gmail.get_messages(query=query_params)
    except Exception as e:
        logger.warning("Fout bij ophalen Gmail messages: %s", e)
        return 0

    EMAIL_DIR.mkdir(parents=True, exist_ok=True)
    if EMAILS_CSV.exists():
        df = pd.read_csv(EMAILS_CSV, sep=";")
    else:
        df = pd.DataFrame(columns=EMAILS_RAW_COLUMNS)

    bestaande_ids = set(df["Id"].astype(str).tolist())
    nieuw = 0

    for message in messages:
        if str(message.id) in bestaande_ids:
            continue
        if message.sender != ALLOWED_SENDER:
            continue

        try:
            dt = pd.to_datetime(message.date)
            df.loc[len(df)] = [
                message.id,
                int(dt.strftime("%Y%m%d")),
                dt.strftime("%H:%M:%S"),
                message.sender,
                message.subject,
                message.plain,
            ]
            nieuw += 1
        except Exception as e:
            logger.warning("Kon Gmail-bericht %s niet parsen: %s", message.id, e)

    if nieuw > 0:
        df["DateKey"] = pd.to_numeric(df["DateKey"], errors="coerce").astype("Int64")
        df.to_csv(EMAILS_CSV, index=False, sep=";", encoding="utf-8")
        logger.info("Gmail fetch: %d nieuwe e-mails toegevoegd aan emails.csv", nieuw)
    else:
        logger.info("Gmail fetch: geen nieuwe e-mails")

    return nieuw


# ── Stap 2: AI-validatie + extractie ─────────────────────────────────────────

def _get_llm():
    """Lazy-init van de Groq LLM. Geeft None terug als import/key faalt."""
    global _llm
    if _llm is not None:
        return _llm
    try:
        from langchain_groq import ChatGroq
    except Exception as e:
        logger.warning("langchain_groq kon niet geïmporteerd worden: %s", e)
        return None
    api_key = os.getenv("groq_API")
    if not api_key:
        logger.warning("Env var 'groq_API' niet gezet — LLM-extractie overgeslagen")
        return None
    try:
        _llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile", groq_api_key=api_key)
    except Exception as e:
        logger.warning("ChatGroq init faalde: %s", e)
        return None
    return _llm


def _ai_validate(mail_text: str) -> bool:
    """Vraagt aan de LLM of een email geaccepteerd of gerejecteerd moet worden."""
    llm = _get_llm()
    if llm is None:
        return False
    prompt = f"""

    Je bent een email analyst. Je taak is om een e-mails rejecten of niet op basis van REGELS die worden opgelijst hieronder.

    Te analyseren e-mail:
    -----------------------
    {mail_text}
    -----------------------


    STRIKTE REGELS VOORDAT EEN EMAIL WORDT GE ACCEPT:
    1. Kijk naar de 'Periode' in de mail (bijv. 09/2025). Dit bepaalt de maand.
    2. Scan de tekst op specifieke datums (bijv. "dinsdag 2 september 2025").
    3. De afstand opgegeven in de mail moet realistisch zijn om te fietsen, niet groter dan 30km
    4. Er mogen geen dubbele dagen instaan

    ANTWOORD ENKEL met het woord 'REJECTED' indien rejected of 'ACCEPTED' indien accepted.:
    """
    try:
        return llm.invoke(prompt).content.strip().upper() == "ACCEPTED"
    except Exception as e:
        logger.warning("LLM-validatie faalde: %s", e)
        return False


def _ai_postal_code(plaats: str) -> str:
    """Vraagt de Belgische postcode op via de LLM. Geeft '' terug bij faal."""
    llm = _get_llm()
    if llm is None:
        return ""
    try:
        return llm.invoke(
            input=f"Geef de Belgische postcode van de plaats {plaats}. GEEF ALLEEN ALS OUTPUT DE POSTCODE"
        ).content.strip()
    except Exception as e:
        logger.warning("LLM-postcode lookup faalde voor '%s': %s", plaats, e)
        return ""


def _extract(text: str) -> list | None:
    """
    Trekt gestructureerde data uit een email-body. Returns None bij parse-fout.
    Output: [StaffID, Entity, Campus, PostalCode, DistanceKM, Period, dag1..dag31]
    """
    try:
        pid       = re.search(r"PersoneelsID:\s*(\d+)", text).group(1)
        entiteit  = re.search(r"Gekozen entiteit:.*-\s*(.*)", text).group(1).strip()
        periode   = re.search(r"Periode:\s*(\d{2}/\d{4})", text).group(1)
        afstand   = float(re.search(r"Afstand:\s*(\d+(?:,\d+)?)", text).group(1).replace(",", "."))
        rit_enkel = int(re.search(r"Totaal aantal dagen enkele rit:\s*(\d+)", text).group(1))
        rit_dubbel = int(re.search(r"Totaal aantal dagen heen-en-terug:\s*(\d+)", text).group(1))
        departure_place = re.search(r"Vertrekplaats:\s*(.*)", text).group(1).strip()
    except (AttributeError, ValueError) as e:
        logger.warning("Email parse-fout: %s", e)
        return None

    totaal_km = afstand * ((rit_dubbel * 2) + rit_enkel)
    postal = _ai_postal_code(departure_place)

    dagen = [0.0] * 31
    dag_regels = re.findall(r"(\w+)\s+(\d+)\s+(\w+)\s+(\d{4}):\s+(.*)", text)
    if rit_dubbel + rit_enkel == len(dag_regels):
        for _, dag_nr, _, _, type_rit in dag_regels:
            idx = int(dag_nr) - 1
            if 0 <= idx < 31:
                dagen[idx] = afstand * 2 if "heen en terug" in type_rit.lower() else afstand

    # Periode '09/2025' → 'sep/25' (locale-onafhankelijk)
    try:
        mm, yyyy = periode.split("/")
        periode_kort = f"{_MONTH_SHORT[int(mm)]}/{yyyy[2:]}"
    except (ValueError, KeyError) as e:
        logger.warning("Kon periode '%s' niet converteren: %s", periode, e)
        return None

    return [pid, entiteit, departure_place, postal, totaal_km, periode_kort] + dagen


# ── Stap 3: Verwerk niet-verwerkte e-mails ───────────────────────────────────

def _load_existing_final() -> pd.DataFrame:
    """
    Lees emails_final.csv. Garandeer dat de EmailId-kolom aanwezig is (legacy
    rijen krijgen NaN). Returnt een lege DataFrame met de juiste schema's als
    het bestand niet bestaat.
    """
    if EMAILS_FINAL_CSV.exists():
        df = pd.read_csv(EMAILS_FINAL_CSV, sep=";")
    else:
        df = pd.DataFrame(columns=EMAILS_FINAL_COLUMNS)

    if "EmailId" not in df.columns:
        df.insert(0, "EmailId", pd.NA)

    return df


def _process_unprocessed_emails() -> int:
    """
    Vergelijkt emails.csv met emails_final.csv (op basis van EmailId-kolom)
    en verwerkt enkel niet-verwerkte e-mails. Returns het aantal nieuw
    geappende rijen in emails_final.csv.
    """
    if not EMAILS_CSV.exists():
        logger.info("emails.csv bestaat niet — niets te verwerken.")
        return 0

    raw = pd.read_csv(EMAILS_CSV, sep=";")
    if raw.empty:
        logger.info("emails.csv is leeg — niets te verwerken.")
        return 0

    final = _load_existing_final()

    verwerkte_ids = set(final["EmailId"].dropna().astype(str).tolist())
    te_verwerken = raw[~raw["Id"].astype(str).isin(verwerkte_ids)]

    if te_verwerken.empty:
        logger.info("Alle e-mails in emails.csv zijn al verwerkt.")
        return 0

    nieuwe_rijen = []
    for _, rij in te_verwerken.iterrows():
        msg = rij.get("Message")
        if not isinstance(msg, str) or not msg.strip():
            continue
        if not _ai_validate(msg):
            logger.info("Email %s: AI rejected", rij["Id"])
            continue
        ext = _extract(msg)
        if ext is None:
            continue
        nieuwe_rijen.append([rij["Id"]] + ext)

    if not nieuwe_rijen:
        logger.info("Geen nieuwe geaccepteerde rijen voor emails_final.csv")
        return 0

    nieuw_df = pd.DataFrame(nieuwe_rijen, columns=EMAILS_FINAL_COLUMNS)
    final = pd.concat([final, nieuw_df], ignore_index=True)

    # Dedup tegen legacy-rijen die nog geen EmailId hadden
    final = final.drop_duplicates(
        subset=["StaffID", "Period", "DistanceKM"], keep="last"
    )

    EMAIL_DIR.mkdir(parents=True, exist_ok=True)
    final.to_csv(EMAILS_FINAL_CSV, index=False, sep=";", encoding="utf-8")
    logger.info("emails_final.csv: %d nieuwe rijen toegevoegd", len(nieuwe_rijen))
    return len(nieuwe_rijen)


# ── Public entrypoint ────────────────────────────────────────────────────────

def fetch_and_process(skip_gmail: bool = False) -> None:
    """
    Volledige flow: haal nieuwe e-mails op uit Gmail en verwerk de
    niet-verwerkte e-mails uit emails.csv. Roep dit aan vóór
    ``fillDimStaff`` / ``fillFactStaffCommute``.

    Skipt zichzelf volledig als de env var ``SKIP_EMAIL_FETCH=1`` gezet is.

    Parameters
    ----------
    skip_gmail : bool
        Sla de Gmail-fetch over (handig als je enkel emails.csv lokaal
        wil herverwerken).
    """
    if os.environ.get("SKIP_EMAIL_FETCH", "").lower() in ("1", "true", "yes"):
        logger.info("SKIP_EMAIL_FETCH gezet — fetcher overgeslagen.")
        return

    if not skip_gmail:
        try:
            _fetch_new_gmail_messages()
        except Exception as e:
            logger.warning("Onverwachte fout bij Gmail-fetch: %s", e)

    try:
        _process_unprocessed_emails()
    except Exception as e:
        logger.warning("Onverwachte fout bij verwerken van e-mails: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    fetch_and_process()
