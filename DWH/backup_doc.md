# SQL Server Backup - Documentatie

## Overzicht

Dit systeem maakt automatisch iedere week (zondag om 23:59) een back-up van een SQL Server database via een Bash-script.

De back-up wordt:
- Automatisch uitgevoerd
- Voorzien van een unieke timestamp
- Veilig opgeslagen als `.bak` bestand
- Gelogd voor controle en debugging

---

# Projectstructuur

```text
/home/vicuser/
├── backup.sh
├── dep/
│   └── .env
└── sql_backups/
    ├── backup.log
    └── *.bak
```

---

# `.env` bestand

Het `.env` bestand bevat de databaseconfiguratie.

Locatie:

```text
/home/vicuser/dep/.env
```

Voorbeeld:

```env
DB_NAME=myDatabase
DB_USER=sa
databasePWD=MijnSterkWachtwoord
```

---

# Backup Script

Locatie:

```text
/home/vicuser/backup.sh
```

## Wat doet het script?

Het script voert automatisch de volgende stappen uit:

1. Laadt databasegegevens uit het `.env` bestand
2. Maakt een timestamp aan voor unieke bestandsnamen
3. Voert een SQL Server backup uit via `sqlcmd`
4. Slaat de backup tijdelijk op in de SQL Server datafolder
5. Verplaatst de backup naar de definitieve backupmap
6. Past bestandsrechten aan

---

# Backup Locaties

## Tijdelijke locatie

SQL Server maakt eerst de backup aan in:

```text
/var/opt/mssql/data/
```

## Definitieve locatie

Daarna wordt het bestand verplaatst naar:

```text
/home/vicuser/sql_backups/
```

---

# Logging

Alle uitvoer van het script wordt opgeslagen in:

```text
/home/vicuser/sql_backups/backup.log
```

Zo kunnen fouten of succesvolle backups eenvoudig gecontroleerd worden.

---

# Bestandsrechten

Na het verplaatsen van de backup:

- Wordt `vicuser` eigenaar van het bestand
- Worden correcte lees- en schrijfrechten ingesteld

---

# Vereisten

Het systeem vereist:

- Microsoft SQL Server
- `sqlcmd` tools
- Schrijfrechten op de backupmappen

---

# Samenvatting

Dit backupsysteem zorgt voor:

- Automatische wekelijkse SQL Server backups
- Veilige opslag van `.bak` bestanden
- Logging van alle backups
- Gebruik van environment variables via `.env`
- Correct beheer van Linux bestandsrechten

