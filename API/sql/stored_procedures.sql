/* ============================================================================
   Stored Procedures voor de DEPI Web API
   ----------------------------------------------------------------------------
   Deze stored procedures implementeren de queries achter de REST-operaties
   van de Flask Web API. Voer dit script één keer uit op de DEPI database.

   Conventies:
     - Naamgeving: sp_<Resource>_<Actie>
     - DateKey is INT in YYYYMMDD-formaat (zie DimDate)
     - Functionele invoer-validatie gebeurt in de Python-laag; de SP's
       gooien zelf RAISERROR bij hard-foute combinaties (bv. onbestaande PK)
============================================================================ */

USE DEPI;
GO

/* ============================================================================
   1. sp_Countings_SincePeriodStart
      Geeft het totaal aantal fietsers voor één telpaal sinds:
        - 'day'   = sinds middernacht (vandaag)
        - 'week'  = sinds maandag van deze week (ISO-week)
        - 'month' = sinds eerste van deze maand
        - 'year'  = sinds 1 januari van dit jaar
      Validatie:
        - @Period moet één van bovenstaande waardes zijn
        - @CountingPointID moet bestaan in DimCountingPoint
============================================================================ */
IF OBJECT_ID('dbo.sp_Countings_SincePeriodStart', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_Countings_SincePeriodStart;
GO

CREATE PROCEDURE dbo.sp_Countings_SincePeriodStart
    @CountingPointID INT,
    @Period VARCHAR(10)
AS
BEGIN
    SET NOCOUNT ON;

    /* ---- Validatie ---- */
    IF @Period NOT IN ('day', 'week', 'month', 'year')
    BEGIN
        RAISERROR('Ongeldige periode. Toegelaten: day, week, month, year.', 16, 1);
        RETURN;
    END

    IF NOT EXISTS (SELECT 1 FROM dbo.DimCountingPoint WHERE CountingPointID = @CountingPointID)
    BEGIN
        RAISERROR('Telpaal met deze ID bestaat niet.', 16, 1);
        RETURN;
    END

    /* ---- Bepaal startdatum (DateKey YYYYMMDD) ---- */
    DECLARE @Today DATE = CAST(GETDATE() AS DATE);
    DECLARE @StartDate DATE;

    IF @Period = 'day'
        SET @StartDate = @Today;
    ELSE IF @Period = 'week'
        /* Maandag als eerste dag van de week */
        SET @StartDate = DATEADD(DAY, 1 - ((DATEPART(WEEKDAY, @Today) + @@DATEFIRST - 2) % 7 + 1), @Today);
    ELSE IF @Period = 'month'
        SET @StartDate = DATEFROMPARTS(YEAR(@Today), MONTH(@Today), 1);
    ELSE IF @Period = 'year'
        SET @StartDate = DATEFROMPARTS(YEAR(@Today), 1, 1);

    DECLARE @StartDateKey INT = CONVERT(INT, FORMAT(@StartDate, 'yyyyMMdd'));
    DECLARE @TodayKey     INT = CONVERT(INT, FORMAT(@Today,     'yyyyMMdd'));

    /* ---- Resultaat ---- */
    SELECT
        @CountingPointID                               AS CountingPointID,
        @Period                                        AS Period,
        @StartDate                                     AS StartDate,
        @Today                                         AS EndDate,
        ISNULL(SUM(fc.TotalCounts), 0)                 AS TotalCounts,
        ISNULL(SUM(fc.DirectionInCounts), 0)           AS DirectionInCounts,
        ISNULL(SUM(fc.DirectionOutCounts), 0)          AS DirectionOutCounts
    FROM dbo.FactCountings fc
    WHERE fc.CountingPointID = @CountingPointID
      AND fc.DateKey BETWEEN @StartDateKey AND @TodayKey;
END
GO


/* ============================================================================
   2. sp_Countings_OnDay
      Geeft het totaal aantal fietsers op één specifieke dag in het verleden.
      Validatie:
        - @Date moet < vandaag zijn
        - @CountingPointID moet bestaan in DimCountingPoint
============================================================================ */
IF OBJECT_ID('dbo.sp_Countings_OnDay', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_Countings_OnDay;
GO

CREATE PROCEDURE dbo.sp_Countings_OnDay
    @CountingPointID INT,
    @Date DATE
AS
BEGIN
    SET NOCOUNT ON;

    /* ---- Validatie ---- */
    IF @Date IS NULL
    BEGIN
        RAISERROR('Datum is verplicht.', 16, 1);
        RETURN;
    END

    IF @Date >= CAST(GETDATE() AS DATE)
    BEGIN
        RAISERROR('Datum moet in het verleden liggen.', 16, 1);
        RETURN;
    END

    IF NOT EXISTS (SELECT 1 FROM dbo.DimCountingPoint WHERE CountingPointID = @CountingPointID)
    BEGIN
        RAISERROR('Telpaal met deze ID bestaat niet.', 16, 1);
        RETURN;
    END

    DECLARE @DateKey INT = CONVERT(INT, FORMAT(@Date, 'yyyyMMdd'));

    SELECT
        @CountingPointID                            AS CountingPointID,
        @Date                                       AS Date,
        ISNULL(SUM(fc.TotalCounts), 0)              AS TotalCounts,
        ISNULL(SUM(fc.DirectionInCounts), 0)        AS DirectionInCounts,
        ISNULL(SUM(fc.DirectionOutCounts), 0)       AS DirectionOutCounts
    FROM dbo.FactCountings fc
    WHERE fc.CountingPointID = @CountingPointID
      AND fc.DateKey = @DateKey;
END
GO


/* ============================================================================
   3. sp_Weather_WindForDay
      Geeft de gemiddelde windsnelheid op 10m hoogte (WindSpeed10m) en de
      hoogste windvlaag (WindGustsSpeed) voor één weerstation op één dag.

      LET OP: in deze DWH bevat FactMeteo.WeatherStationKey dezelfde waarde
              als DimWeatherStation.WeatherStationID (en niet de IDENTITY
              surrogate key WeatherStationKey). De JOIN gebeurt dus op
              ws.WeatherStationID = fm.WeatherStationKey.

      De API-parameter heet @WeatherStationID — dit is de bron-ID die in
      beide tabellen voorkomt.

      Validatie:
        - @WeatherStationID moet bestaan in DimWeatherStation
        - @Date mag niet in de toekomst liggen
============================================================================ */
IF OBJECT_ID('dbo.sp_Weather_WindForDay', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_Weather_WindForDay;
GO

CREATE PROCEDURE dbo.sp_Weather_WindForDay
    @WeatherStationID VARCHAR(50),
    @Date DATE
AS
BEGIN
    SET NOCOUNT ON;

    IF @Date IS NULL
    BEGIN
        RAISERROR('Datum is verplicht.', 16, 1);
        RETURN;
    END

    IF @Date > CAST(GETDATE() AS DATE)
    BEGIN
        RAISERROR('Datum mag niet in de toekomst liggen.', 16, 1);
        RETURN;
    END

    IF @WeatherStationID IS NULL OR LTRIM(RTRIM(@WeatherStationID)) = ''
    BEGIN
        RAISERROR('WeatherStationID is verplicht.', 16, 1);
        RETURN;
    END

    IF NOT EXISTS (
        SELECT 1 FROM dbo.DimWeatherStation
        WHERE WeatherStationID = @WeatherStationID
    )
    BEGIN
        RAISERROR('Weerstation met deze ID bestaat niet.', 16, 1);
        RETURN;
    END

    DECLARE @DateKey INT = CONVERT(INT, FORMAT(@Date, 'yyyyMMdd'));

    /*  FactMeteo.WeatherStationKey == DimWeatherStation.WeatherStationID
        (zelfde bron-ID; in deze DWH bestaat er geen aparte surrogate key
        op DimWeatherStation). JOIN met expliciete CAST zodat type-mismatch
        (INT vs VARCHAR) geen impliciete conversie-index-scan veroorzaakt. */
    SELECT
        ws.WeatherStationID                           AS WeatherStationID,
        ws.Name                                       AS WeatherStationName,
        @Date                                         AS Date,
        AVG(CAST(fm.WindSpeed10m  AS DECIMAL(10,2)))  AS AvgWindSpeed10m,
        MAX(fm.WindGustsSpeed)                        AS MaxWindGustsSpeed
    FROM dbo.DimWeatherStation ws
    LEFT JOIN dbo.FactMeteo fm
           ON CAST(fm.WeatherStationKey AS VARCHAR(50)) = ws.WeatherStationID
          AND fm.DateKey = @DateKey
    WHERE ws.WeatherStationID = @WeatherStationID
    GROUP BY ws.WeatherStationID, ws.Name;
END
GO


/* ============================================================================
   4. sp_BlueBike_AvailabilityLast7Days
      Geeft per Blue Bike-locatie het hoogste en laagste aantal beschikbare
      fietsen in de laatste 7 dagen t.o.v. nu. Geen invoer nodig.
============================================================================ */
IF OBJECT_ID('dbo.sp_BlueBike_AvailabilityLast7Days', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_BlueBike_AvailabilityLast7Days;
GO

CREATE PROCEDURE dbo.sp_BlueBike_AvailabilityLast7Days
AS
BEGIN
    SET NOCOUNT ON;

    /* DateKey = YYYYMMDD; we vergelijken op DateKey én TimeKey want fietsen
       kunnen meerdere keren per dag gemeten zijn. Zonder TimeKey ben je niet
       exact 7 dagen geleden t.o.v. NU.                                        */
    DECLARE @NowDate DATE = CAST(GETDATE() AS DATE);
    DECLARE @NowTimeKey INT = DATEPART(HOUR, GETDATE()) * 100 + DATEPART(MINUTE, GETDATE());

    DECLARE @StartDate DATE = DATEADD(DAY, -7, @NowDate);
    DECLARE @StartDateKey INT = CONVERT(INT, FORMAT(@StartDate, 'yyyyMMdd'));
    DECLARE @NowDateKey   INT = CONVERT(INT, FORMAT(@NowDate,   'yyyyMMdd'));

    SELECT
        bb.BlueBikeStationKey,
        bb.LocationName,
        bb.Latitude,
        bb.Longitude,
        MIN(f.TotalBikesAvailable) AS MinAvailable,
        MAX(f.TotalBikesAvailable) AS MaxAvailable,
        COUNT(*)                    AS Measurements
    FROM dbo.DimBlueBikeStation bb
    LEFT JOIN dbo.FactBlueBike f
           ON f.BlueBikeStationKey = bb.BlueBikeStationKey
          /* Tussen 7 dagen geleden (vanaf @StartDate, alle uren) en nu */
          AND (
                (f.DateKey >  @StartDateKey AND f.DateKey <  @NowDateKey)
             OR (f.DateKey =  @StartDateKey AND f.TimeKey >= @NowTimeKey)
             OR (f.DateKey =  @NowDateKey   AND f.TimeKey <= @NowTimeKey)
          )
    GROUP BY bb.BlueBikeStationKey, bb.LocationName, bb.Latitude, bb.Longitude
    ORDER BY bb.BlueBikeStationKey;
END
GO


/* ============================================================================
   5. sp_HealthCheck
      Eenvoudige check dat de DB bereikbaar is en dat de essentiële tabellen
      bestaan. Wordt gebruikt door GET /api/v1/health.
============================================================================ */
IF OBJECT_ID('dbo.sp_HealthCheck', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_HealthCheck;
GO

CREATE PROCEDURE dbo.sp_HealthCheck
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        'ok'                                                              AS Status,
        DB_NAME()                                                         AS DatabaseName,
        SYSUTCDATETIME()                                                  AS ServerTimeUtc,
        (SELECT COUNT(*) FROM dbo.DimCountingPoint)                       AS CountingPoints,
        (SELECT COUNT(*) FROM dbo.DimWeatherStation)                      AS WeatherStations,
        (SELECT COUNT(*) FROM dbo.DimBlueBikeStation)                     AS BlueBikeStations;
END
GO


/* ============================================================================
   6. sp_List_CountingPoints
      Extra resource: alle telpalen oplijsten (voor /counting-points GET).
============================================================================ */
IF OBJECT_ID('dbo.sp_List_CountingPoints', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_List_CountingPoints;
GO

CREATE PROCEDURE dbo.sp_List_CountingPoints
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        CountingPointID,
        CustomID,
        CountingPointName,
        Latitude,
        Longitude,
        FirstData,
        Granularity,
        Directional,
        DomainName
    FROM dbo.DimCountingPoint
    ORDER BY CountingPointName;
END
GO


/* ============================================================================
   7. sp_List_WeatherStations
      Extra resource: alle weerstations oplijsten.
============================================================================ */
IF OBJECT_ID('dbo.sp_List_WeatherStations', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_List_WeatherStations;
GO

CREATE PROCEDURE dbo.sp_List_WeatherStations
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        WeatherStationID,
        Name,
        Latitude,
        Longitude,
        Altitude
    FROM dbo.DimWeatherStation
    ORDER BY Name;
END
GO


/* ============================================================================
   8. sp_List_BlueBikeStations
      Extra resource: alle Blue Bike-locaties oplijsten.
============================================================================ */
IF OBJECT_ID('dbo.sp_List_BlueBikeStations', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_List_BlueBikeStations;
GO

CREATE PROCEDURE dbo.sp_List_BlueBikeStations
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        BlueBikeStationKey,
        LocationName,
        Latitude,
        Longitude
    FROM dbo.DimBlueBikeStation
    ORDER BY LocationName;
END
GO


/* ============================================================================
   9. sp_Countings_TopBusiestPoints
      Extra resource: top N drukste telpalen op een gegeven datum.
      Validatie: @TopN > 0, @Date <= vandaag.
============================================================================ */
IF OBJECT_ID('dbo.sp_Countings_TopBusiestPoints', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_Countings_TopBusiestPoints;
GO

CREATE PROCEDURE dbo.sp_Countings_TopBusiestPoints
    @Date DATE,
    @TopN INT = 10
AS
BEGIN
    SET NOCOUNT ON;

    IF @Date IS NULL OR @Date > CAST(GETDATE() AS DATE)
    BEGIN
        RAISERROR('Datum is verplicht en mag niet in de toekomst liggen.', 16, 1);
        RETURN;
    END

    IF @TopN IS NULL OR @TopN <= 0 OR @TopN > 1000
    BEGIN
        RAISERROR('TopN moet tussen 1 en 1000 liggen.', 16, 1);
        RETURN;
    END

    DECLARE @DateKey INT = CONVERT(INT, FORMAT(@Date, 'yyyyMMdd'));

    SELECT TOP (@TopN)
        cp.CountingPointID,
        cp.CountingPointName,
        SUM(fc.TotalCounts) AS TotalCounts
    FROM dbo.FactCountings fc
    INNER JOIN dbo.DimCountingPoint cp
            ON cp.CountingPointID = fc.CountingPointID
    WHERE fc.DateKey = @DateKey
    GROUP BY cp.CountingPointID, cp.CountingPointName
    ORDER BY SUM(fc.TotalCounts) DESC;
END
GO

PRINT 'Alle stored procedures aangemaakt.';
