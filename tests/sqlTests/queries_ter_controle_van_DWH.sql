-- Het aantal records in DimDate: 3653 + Verklaar -> vanaf 2017 (data vanaf 2010 in dimdate)
SELECT COUNT(*) FROM DimDate
where DateKey > 20161230

-- Het aantal records in DimTime: 1440 + Verklaar -> 60 m * 24 h = 1440
SELECT COUNT(*) FROM DimTime

-- Het aantal weerstations: 14
SELECT COUNT(*) FROM DimWeatherstation

/*
Antwerpen	3
Limburg	1
Oost-Vlaanderen	1
Vlaams-Brabant	1
West-Vlaanderen	3
*/
SELECT dl.province, COUNT(dw.WeatherStationID)
FROM DimWeatherstation dw JOIN DimLocation dl ON dw.LocationKey = dl.LocationKey
GROUP BY dl.province

/*
28.55	-3.30	22.99	-6.01	34.97	-2.50	34.87
*/
SELECT MAX(TempAvg), MIN(TempAvg),  MAX(TempMin), MIN(TempMin), MAX(TempMax), MIN(TempMax), MAX(PrecipQuantity)
FROM DimWeatherstation dw JOIN FactMeteo fm ON dw.WeatherStationID = fm.WeatherStationKey
WHERE dw.Name = 'Zeebrugge'

/*
BEITEM	2279
BUZENOL	2279
DE HAAN	387
DIEPENBEEK	2279
DOURBES	2279
ERNAGE	2279
HUMAIN	2279
MELLE	2279
MONT RIGI	2279
RETIE	2279
SINT-KATELIJNE-WAVER	2279
STABROEK	2279
UCCLE	2279
ZEEBRUGGE	2279
*/
SELECT dw.Name, COUNT(*)
FROM DimWeatherStation dw JOIN FactMeteo fm ON dw.WeatherStationID = fm.WeatherStationKey
WHERE DateKey >= 20200101
GROUP BY dw.Name


-- Het aantal records in DimTransportMode: 8
SELECT COUNT(*) FROM DimTransportType

-- De CO2 emissie voor Airplane +700km: 0.3 -> andere naam
SELECT * FROM DimTransportType WHERE VehicleType = 'Vliegtuig+700'

-- Het aantal records met CO2 uitstoot groter dan 0.2: 6 -> aangepast naar niet, want er zijn er maar 2 > 0.2
SELECT COUNT(*) FROM DimTransportType WHERE not(CO2PerKM > 0.2);
SELECT COUNT(*) FROM DimTransportType WHERE CO2PerKM > 0.2

-- Het aantal Blue bike stations: 249 -> 253
SELECT COUNT(*) FROM DimBlueBikeStation

-- Het aantal Blue bike stations per provincie
--province	(No column name)
--NULL	2 -> 0
--Antwerpen	41 -> 40
--Brussel	4 -> 0
--Henegouwen	1 -> 1
--Limburg	21 -> 21
--Luik	1 -> 1
--Luxemburg	1 -> 1
--Namen	1 -> 1
--Oost-Vlaanderen	84 -> 86
--Vlaams-Brabant	71 -> 79
--Waals-Brabant	1 -> 1
--West-Vlaanderen	21 -> 22

SELECT dl.Province, COUNT(*)
FROM DimBlueBikeStation db JOIN DimLocation dl ON db.LocationKey = dl.LocationKey
GROUP BY dl.Province

-- Het aantal Blue bike stations in Gent: 6 -> 5
SELECT COUNT(*)
FROM DimBlueBikeStation db JOIN DimLocation dl ON db.LocationKey = dl.LocationKey
WHERE dl.Municipality LIKE '%Gent%'

-- Het aantal Blue bike stations met station in de naam: 132 -> 131
SELECT COUNT(*)
FROM DimBlueBikeStation db 
WHERE LocationName LIKE '%station%'

-- Het gemiddeld aantal beschikbare fietsen in Oostende Station over alle data heen: 72.4382151029 -> 83
SELECT AVG(TotalBikesAvailable)
FROM FactBlueBike fb JOIN DimBlueBikeStation db ON fb.BlueBikeStationKey = db.BlueBikeStationKey
WHERE db.LocationName = 'Oostende station'

-- Het aantal records aanwezig in FactBlueBikeAvailability
SELECT COUNT(*) FROM FactBlueBike

-- Het aantal records aanwezig in FactBlueBikeAvailability voor Gent Dampoort
SELECT COUNT(*)
FROM FactBlueBike fb JOIN DimBlueBikeStation db ON fb.BlueBikeStationKey = db.BlueBikeStationKey
WHERE db.LocationName LIKE '%Gent-Dampoort%'

-- Het aantal telpalen: 354 -> 356
SELECT COUNT(*) FROM DimCountingPoint

-- Het aantal telpalen in postcode 9800: 5 -> 2, want: 1 in vosselare (deelgemeente 9850), 2 in nazareth (net op de grens)
SELECT COUNT(*) 
FROM DimCountingPoint dc JOIN DimLocation dl ON dc.LocationKey = dl.LocationKey
WHERE PostalCode = '9800'

-- Alle telpalen waar Wervik in de naam voorkomt
--counting_point_key	counting_point_id	custom_id	counting_point_name	latitude	longitude	first_data	granularity	directional	direction_name_in	direction_name_out	domain_id	domain_name
--118	300024592	Fietstel_Wervik2	Wervik F372 Menenstraat (Zuid)	50.805550000000000	3.092100000000000	2022-06-03 00:00:00.000	PT15M	1	Geluwe	Menen	6517	Vlaamse Overheid A. Wegen en Verkeer
--119	300024594	Fietstel_Wervik1	Wervik F372 Menenstraat (Noord)	50.805800000000000	3.091540000000000	2022-06-03 00:00:00.000	PT15M	1	Menen	Geluwe	6517	Vlaamse Overheid A. Wegen en Verkeer
SELECT *
FROM DimCountingPoint 
WHERE CountingPointName LIKE '%Wervik%'

-- Alle telpalen in Mechelen: 8
SELECT COUNT(*)
FROM DimCountingPoint dc JOIN DimLocation dl ON dc.LocationKey = dl.LocationKey
WHERE MainMunicipality = 'Sint-Niklaas' OR Municipality = 'Mechelen'

-- Het aantal telpalen per provincie
--ANTWERPEN	102 -> 105
--HENEGOUWEN	1 -> 0
--LIMBURG	80 -> 77
--OOST-VLAANDEREN	48 -> 52
--VLAAMS-BRABANT	71 -> 68
--WEST-VLAANDEREN	52 -> 54
SELECT Province, COUNT(*)
FROM DimCountingPoint dc  JOIN DimLocation dl ON dc.LocationKey = dl.LocationKey
GROUP BY Province

-- Het totaal aantal getelde fietsers in 2025 aan de fietstelpaal met naam Fintele
-- 365	75346	518	2
SELECT COUNT(*), SUM(TotalCounts), MAX(DirectionInCounts), MIN(DirectionOutCounts) 
FROM FactCountings fc JOIN DimCountingPoint dc ON fc.CountingPointID = dc.CountingPointID
WHERE dc.CountingPointName LIKE '%Fintele%' AND DateKey >= 20250101 AND DateKey <= 20251231

-- Het totaal aantal getelde fietsers in 2024 aan de fietstelpaal met naam Jaagpad Bovenschelde
-- 366	177819	881	18
SELECT COUNT(*), SUM(TotalCounts), MAX(DirectionInCounts), MIN(DirectionOutCounts) 
FROM FactCountings fc JOIN DimCountingPoint dc ON fc.CountingPointID = dc.CountingPointID
WHERE dc.CountingPointName LIKE '%Jaagpad Bovenschelde%' AND DateKey >= 20240101 AND DateKey <= 20241231


-- De dag, locatie en total_counts van de telpaal met het grootste aantal countings
-- 20230625	Antwerpen - Desguinlei (Zuid)	56517
SELECT DateKey, dc.CountingPointName, fc.TotalCounts
FROM FactCountings fc JOIN DimCountingPoint dc ON fc.CountingPointID = dc.CountingPointID
WHERE TotalCounts = (SELECT MAX(TotalCounts) FROM FactCountings)

-- Aantal records met total_counts = 0 -> 2206, in en out zijn 0, moeten we die dan verwijderen? (klopt met site)
SELECT COUNT(*)
FROM FactCountings fc 
WHERE TotalCounts = 0

-- Geef de TOP 5 van records met total_counts = 1230 gesorteerd op datum
--date_key	counting_point_name	total_counts
--20200325	Turnhout F15 Jaagpad Kanaal Dessel-Schoten	1230
--20200424	Oudenaarde - Jaagpad Bovenschelde	1230
--20200717	Leuven F8 Zijpstraat	1230
--20200816	Antwerpen - Zurenborgbrug	1230
--20210308	Boechout F11 Victor Heylenlei	1230
SELECT TOP 5 DateKey, dc.CountingPointName, fc.TotalCounts
FROM FactCountings fc JOIN DimCountingPoint dc ON fc.CountingPointID = dc.CountingPointID
WHERE TotalCounts = 1230
ORDER BY fc.DateKey

-- Zijn er records waarbij het totaal niet gelijk is aan de som van IN en OUT als IN en OUT NIET NULL zijn
SELECT COUNT(*)
FROM FactCountings
WHERE DirectionInCounts IS NOT NULL AND DirectionOutCounts IS NOT NULL AND TotalCounts != (DirectionInCounts + DirectionOutCounts)

-- Het aantal employees in DimEmployee (afkomstig van de fietsvergoedingen): 462
SELECT COUNT(*) FROM DimStaff

--  Het aantal employees in DimEmployee (afkomstig van de fietsvergoedingen) uit het departement ALG: 13
SELECT COUNT(*) FROM DimStaff ds JOIN DimDepartement dd ON ds.DepartementKey = dd.DepartementKey WHERE dd.DepartementName = 'ALG'

-- Het aantal employees in DimEmployee per campus

--main_campus	(No column name)
--Campus Aalst	5
--Campus Bijloke	35
--Campus Grote Sikkel	8
--Campus Ledeganck	30
--Campus Melle	13
--Campus Mercator	37
--Campus Schoonmeersen	247
--campus Schoonmeersen Zuid (o.a. gebouw T)	11
--Campus Vesalius	35
--De Wijnaert	23
--GO! CVO Panta Rhei de Avondschool	3
--Het Perspectief	1
--niet meer in dienst	4
--site Bottelare	2
--site Buchtenstraat	3
--site Offerlaan	5

SELECT Campus, COUNT(*)
FROM DimStaff
GROUP BY Campus

-- startdate en enddate toegevoegd aan DimEmployee?
-- moet gebeuren
select * from DimStaff
-- Het aantal records in FactDepartmentHeadcount: 1426
-- aanpassen
SELECT COUNT(*) FROM FactDepartement

-- Het aantal personeelsleden in het departement DBO, DIT en DHR op 1 januari 2025
--4	DBO	20250101	4	221
--10	DHR	20250101	10	1
--12	DIT	20250101	12	61
-- nog eens bekijken (slowly changing)
SELECT * 
FROM DimDepartement dd JOIN FactDepartement fd ON dd.DepartementKey = fd.DepartementKey
WHERE DateKey = 20250101 AND dd.DepartementName IN ('DBO', 'DIT', 'DHR')

-- Het gemiddeld aantal personeelsleden per jaar voor het departement DBO
--2024	241
--2025	221
--2026	192

SELECT dt.Year, AVG(fd.AmountOfWorkers)
FROM DimDepartement dd JOIN FactDepartement fd ON dd.DepartementKey = fd.DepartementKey
JOIN DimDate dt ON dt.DateKey = fd.DateKey
WHERE dd.DepartementName = 'DBO'
GROUP BY dt.Year

-- Het aantal records in de de mobiliteitsbevraging -> 665
SELECT COUNT(*) 
FROM DimWorkerMobility

-- Het aantal personeelsleden per vervoersmiddel
/*
Auto	201
Bus	15
Fiets	264
Trein	113
*/
SELECT dtt.VehicleType, COUNT(DISTINCT fwm.WorkerID)
FROM FactWorkerMobility fwm
JOIN DimTransportType dtt ON fwm.TransportKey = dtt.TransportKey
GROUP BY dtt.VehicleType

-- Het aantal treinen dat gisteren aankwam in Kortrijk
-- 20260329 = 112
SELECT SUM(fa.AmountOfArrivals)
FROM FactTrainArrival fa
JOIN DimStation ds ON fa.StationKey = ds.StationKey
WHERE ds.StationName LIKE '%Kortrijk%'
  AND fa.DateKey = CONVERT(INT, CONVERT(VARCHAR(8), DATEADD(DAY, -1, GETDATE()), 112))


