IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'DEPI')
BEGIN
    CREATE DATABASE DEPI;
END
GO

USE DEPI;
GO

-- DimDate 
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimDate')
BEGIN
    CREATE TABLE DimDate (
        DateKey INT PRIMARY KEY, 
        FullDateAlternateKey DATE,
        DayOfMonth INT,
        EnglishDayNameOfWeek VARCHAR(50),
        DutchDayNameOfWeek VARCHAR(50),
        DayOfWeek INT,
        DayOfWeekInMonth INT,
        DayOfWeekInYear INT,
        DayOfQuarter INT,
        DayOfYear INT,
        WeekOfMonth INT,
        WeekOfQuarter INT,
        WeekOfYear INT,
        Month INT,
        EnglishMonthName VARCHAR(50),
        DutchMonthName VARCHAR(50),
        MonthOfQuarter INT,
        Quarter INT,
        QuarterName CHAR(2),
        Year INT,
        MonthYear VARCHAR(20),
        MMYYYY CHAR(6),

        IsHoliday BIT,
        HolidayName VARCHAR(255),

        IsWeekend BIT,
        IsWorkingDay BIT,

        IsSchoolHoliday BIT,
        SchoolHolidayName VARCHAR(255)
    );
END

-- DimTime
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimTime')
BEGIN
    CREATE TABLE DimTime (
        TimeKey INT PRIMARY KEY, 
        FullTime TIME,
        Hour INT,
        Minute INT,
        AMPM CHAR(2),
        Hour12 INT
    );
END

-- DimLocation
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimLocation')
BEGIN
    CREATE TABLE DimLocation (
        LocationKey INT PRIMARY KEY IDENTITY(1,1),
        PostalCode VARCHAR(10),
        Municipality VARCHAR(100),
        MainMunicipality VARCHAR(100),
        Province VARCHAR(100)
        CONSTRAINT UQ_Location UNIQUE (PostalCode, Municipality, MainMunicipality, Province)
    );
END

-- DimTransportType
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimTransportType')
BEGIN
    CREATE TABLE DimTransportType (
        TransportKey INT PRIMARY KEY IDENTITY(1,1),
        VehicleType VARCHAR(100), -- Fiets, Trein, Auto, etc.
        CO2PerKM DECIMAL(10,5) -- Uit 'uitstoot_in_kg_CO2_per_km.csv'
    );
END

-- DimDepartement
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimDepartement')
BEGIN
    CREATE TABLE DimDepartement (
        DepartementKey INT PRIMARY key IDENTITY(1,1),
        DepartementName VARCHAR(255),
        StartDate INT,
        EndDate INT,
        CONSTRAINT FK_DimDepartement_StartDate FOREIGN KEY (StartDate) REFERENCES DimDate(DateKey),
        CONSTRAINT FK_DimDepartement_EndDate FOREIGN KEY (EndDate) REFERENCES DimDate(DateKey)
    );
END

-- DimStaff
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimStaff')
BEGIN
    CREATE TABLE DimStaff (
        StaffKey INT PRIMARY KEY IDENTITY(1,1),
        StaffID VARCHAR(50),
        Campus VARCHAR(100),
        DepartementKey INT, 
        CONSTRAINT FK_DimStaff_Departement 
            FOREIGN KEY (DepartementKey) REFERENCES DimDepartement(DepartementKey)
        -- LocationKey INT, --fictieve data want postalCode is fictief
        -- CONSTRAINT FK_DimStaff_Location FOREIGN KEY (LocationKey) REFERENCES DimLocation(LocationKey)
    );
END

-- DimWorkerMobility
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimWorkerMobility')
BEGIN
    CREATE TABLE DimWorkerMobility (
        WorkerID INT PRIMARY KEY IDENTITY(1,1),
        ResponseID VARCHAR(50) UNIQUE NOT NULL,
        RecordDate INT NOT NULL,
        Latitude FLOAT NULL,
        Longitude FLOAT NULL,
        WorkPlace VARCHAR(100) NULL,
        WorkFunction VARCHAR(100) NULL,
        WorkRegime VARCHAR(100) NULL,
        HomeWork VARCHAR(100) NULL,
        Finished BIT NOT NULL,
        LocationKey INT NULL,
        CONSTRAINT FK_DimWorkerMobility_Location
            FOREIGN KEY (LocationKey)
            REFERENCES DimLocation(LocationKey)
    );
END

-- DimStation
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimStation')
BEGIN
    CREATE TABLE DimStation (
        StationKey INT PRIMARY KEY IDENTITY(1,1),
        URI VARCHAR(50) NOT NULL,
        StationName VARCHAR(255) NOT NULL,
        Latitude DECIMAL(9,6) NOT NULL,
        Longitude DECIMAL(9,6) NOT NULL,
        LocationKey INT,
        CONSTRAINT UQ_DimStation_URI UNIQUE (URI),
        CONSTRAINT FK_DimStation_Location FOREIGN KEY (LocationKey) REFERENCES DimLocation(LocationKey)
    );
END

-- DimBlueBikeStation
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimBlueBikeStation')
BEGIN
    CREATE TABLE DimBlueBikeStation (
        BlueBikeStationKey INT PRIMARY KEY,
        LocationName VARCHAR(255),
        Latitude DECIMAL(9,6) NOT NULL,
        Longitude DECIMAL(9,6) NOT NULL,
        LocationKey INT NOT NULL,
        CONSTRAINT FK_DimBlueBike_Location FOREIGN KEY (LocationKey) REFERENCES DimLocation(LocationKey)
    );
END

-- DimCountingPoint
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimCountingPoint')
BEGIN
    CREATE TABLE DimCountingPoint (
        CountingPointID INT PRIMARY KEY,
        CustomID VARCHAR(50),
        CountingPointName VARCHAR(255),
        Latitude DECIMAL(9,6),
        Longitude DECIMAL(9,6),
        FirstData DATE,
        Granularity VARCHAR(50),
        Directional BIT,
        DirectionNameIn VARCHAR(100),
        DirectionNameOut VARCHAR(100),
        DomainID INT,
        DomainName VARCHAR(100),
        Description NVARCHAR(MAX),
        LocationKey INT,
        CONSTRAINT FK_DimCountingPoint_Location FOREIGN KEY (LocationKey) REFERENCES DimLocation(LocationKey)
    );
END

-- DimWeatherStation
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimWeatherStation')
BEGIN
    CREATE TABLE DimWeatherStation (
        WeatherStationKey INT IDENTITY(1,1) PRIMARY KEY,
        WeatherStationID VARCHAR(50),
        Name VARCHAR(255) ,
        Point VARCHAR(100),
        Latitude DECIMAL(9,6) UNIQUE,
        Longitude DECIMAL(9,6) UNIQUE,
        Altitude DECIMAL(7,2),
        LocationKey INT, -- op basis van province
        SnapshotDate DATE
    );
END

GO

IF COL_LENGTH('dbo.DimDepartement', 'StartDate') IS NULL
BEGIN
    ALTER TABLE dbo.DimDepartement
    ADD StartDate INT NULL;
END

GO

IF COL_LENGTH('dbo.DimDepartement', 'EndDate') IS NULL
BEGIN
    ALTER TABLE dbo.DimDepartement
    ADD EndDate INT NULL;
END

GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_DimDepartement_StartDate')
BEGIN
    ALTER TABLE dbo.DimDepartement
    WITH CHECK ADD CONSTRAINT FK_DimDepartement_StartDate
    FOREIGN KEY (StartDate) REFERENCES dbo.DimDate(DateKey);
END

GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_DimDepartement_EndDate')
BEGIN
    ALTER TABLE dbo.DimDepartement
    WITH CHECK ADD CONSTRAINT FK_DimDepartement_EndDate
    FOREIGN KEY (EndDate) REFERENCES dbo.DimDate(DateKey);
END

-- DimStudent
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'DimStudent')
BEGIN
    CREATE TABLE DimStudent (
        StudentKey INT PRIMARY KEY IDENTITY(1,1),

        StudentName VARCHAR(255),
        DepartementKey INT,

        CONSTRAINT FK_DimStudent_Departement 
            FOREIGN KEY (DepartementKey) REFERENCES DimDepartement(DepartementKey)
    );
END

-- FactCountings
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactCountings')
BEGIN 
    CREATE TABLE FactCountings (
        CountingPointID INT,
        DateKey INT,
        DirectionInCounts INT,
        DirectionOutCounts INT,
        TotalCounts INT,
        PRIMARY KEY (CountingPointID, DateKey),
        CONSTRAINT FK_FactCountings_CountingPoint FOREIGN KEY (CountingPointID) 
            REFERENCES DimCountingPoint(COuntingPointID),
        CONSTRAINT FK_FactCountings_Date FOREIGN KEY (DateKey) 
            REFERENCES DimDate(DateKey)
    );
END

-- FactMeteo 
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactMeteo')
BEGIN 
    CREATE TABLE FactMeteo (
        MeteoKey INT PRIMARY KEY IDENTITY(1,1),
        DateKey INT,
        WeatherStationKey INT,
        PrecipQuantity DECIMAL(10,2),
        TempAvg DECIMAL(5,2),
        TempMax DECIMAL(5,2),
        TempMin DECIMAL(5,2),
        TempGrassPt100Avg DECIMAL(5,2),
        TempSoilAvg DECIMAL(5,2),
        TempSoilAvg5cm DECIMAL(5,2),
        TempSoilAvg10cm DECIMAL(5,2),
        TempSoilAvg20cm DECIMAL(5,2),
        TempSoilAvg50cm DECIMAL(5,2),
        WindSpeed10m DECIMAL(10,2),
        WindSpeedAvg30m DECIMAL(10,2),
        WindGustsSpeed DECIMAL(10,2),
        HumidityRelShelterAvg DECIMAL(5,2),
        Pressure DECIMAL(10,2),
        SunDuration DECIMAL(10,2),
        ShortWaveFromSkyAvg DECIMAL(10,2),
        SunIntAvg DECIMAL(10,2),
        CONSTRAINT FK_FactMeteo_Date FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
        CONSTRAINT UQ_FactMeteo UNIQUE (DateKey, WeatherStationKey)
    );
END

-- FactStaffCommute
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactStaffCommute')
BEGIN 
    CREATE TABLE FactStaffCommute (
        StaffCommuteKey INT PRIMARY KEY IDENTITY(1,1),
        StaffKey INT,
        DateKey INT,
        Period VARCHAR(20),
        DistanceKM DECIMAL(10,2),
        CONSTRAINT FK_FactStaff_Staff FOREIGN KEY (StaffKey) REFERENCES DimStaff(StaffKey),
        CONSTRAINT FK_FactStaff_Date FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
    );
END

-- FactBlueBike
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactBlueBike')
BEGIN 
    CREATE TABLE FactBlueBike (
        BlueBikeStationKey INT NOT NULL,
        DateKey INT NOT NULL,
        TimeKey INT NOT NULL,
        TotalBikesAvailable INT NOT NULL,
        EBikesAvailable INT NOT NULL,
        BlueBikesAvailable INT NOT NULL,
        MaxCapacity INT NOT NULL,
        BikesDefect INT NOT NULL,
        BikesInUse INT NULL,
        LinkedStationKey INT NULL,

        CONSTRAINT PK_FactBlueBike PRIMARY KEY (BlueBikeStationKey, DateKey, TimeKey),
        CONSTRAINT FK_FactBlueBike_DimBlueBikeStation
            FOREIGN KEY (BlueBikeStationKey)
            REFERENCES DimBlueBikeStation (BlueBikeStationKey),
        CONSTRAINT FK_FactBlueBike_DimDate
            FOREIGN KEY (DateKey)
            REFERENCES DimDate (DateKey),
        CONSTRAINT FK_FactBlueBike_DimTime
            FOREIGN KEY (TimeKey)
            REFERENCES DimTime (TimeKey),
        CONSTRAINT FK_FactBlueBike_DimStation
            FOREIGN KEY (LinkedStationKey)
            REFERENCES DimStation (StationKey)
    );
END

-- FactWorkerMobility
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactWorkerMobility')
BEGIN 
    CREATE TABLE FactWorkerMobility (
        WorkerMobilityKey INT PRIMARY KEY IDENTITY(1,1),
        WorkerID INT NOT NULL,
        DateKey INT NOT NULL,
        TransportKey INT NULL,
        TravelTime FLOAT NULL,
        TravelDistance FLOAT NULL,
        TotalEmission DECIMAL(18,5) NULL,
        CONSTRAINT FK_FactStudent_Student FOREIGN KEY (WorkerID) REFERENCES DimWorkerMobility(WorkerID),
        CONSTRAINT FK_FactStudent_Date FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
        CONSTRAINT FK_FactStudent_Transport FOREIGN KEY (TransportKey) REFERENCES DimTransportType(TransportKey),
    );
END

-- FactTrainArrival
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactTrainArrival')
BEGIN 
    CREATE TABLE FactTrainArrival (
        StationKey       INT NOT NULL,
        DateKey          INT NOT NULL,
        StartTime        INT NOT NULL,
        EndTime          INT NOT NULL,
        AmountOfArrivals INT NOT NULL,
        PRIMARY KEY (StationKey, DateKey, StartTime),
        CONSTRAINT FK_FactTrainArrival_DimStation
            FOREIGN KEY (StationKey)
            REFERENCES DimStation (StationKey),
        CONSTRAINT FK_FactTrainArrival_DimDate
            FOREIGN KEY (DateKey)
            REFERENCES DimDate (DateKey),
        CONSTRAINT FK_FactTrainArrival_StartTime   
            FOREIGN KEY (StartTime)  
            REFERENCES DimTime(TimeKey),
        CONSTRAINT FK_FactTrainArrival_EndTime     
            FOREIGN KEY (EndTime)    
            REFERENCES DimTime(TimeKey)
    )
END

-- FactDepartement
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactDepartement')
BEGIN 
    CREATE TABLE FactDepartement (
        DateKey INT,
        DepartementKey INT,
        AmountOfWorkers INT,
        PRIMARY KEY (DateKey, DepartementKey),
        CONSTRAINT FK_factDepartement_Date FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
        CONSTRAINT Fk_factDepartement_Departement FOREIGN KEY (DepartementKey) REFERENCES DimDepartement(DepartementKey)
    )
END

-- FactStudentMobility
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'FactStudentMobility')
BEGIN
    CREATE TABLE FactStudentMobility (
        MobilityKey INT PRIMARY KEY IDENTITY(1,1),
        StudentKey INT,
        DateKey INT,
        TransportKey INT,
        DistanceKM DECIMAL(10,2),

        CONSTRAINT FK_FactStudentMobility_Student 
            FOREIGN KEY (StudentKey) REFERENCES DimStudent(StudentKey),

        CONSTRAINT FK_FactStudentMobility_Date 
            FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),

        CONSTRAINT FK_FactStudentMobility_Transport 
            FOREIGN KEY (TransportKey) REFERENCES DimTransportType(TransportKey)
    );
END

-- Staging table
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'stg_FactTrainArrival')
BEGIN
    CREATE TABLE stg_FactTrainArrival (
        StationKey  INT          NOT NULL,
        DateKey     INT          NOT NULL,
        TimeKey     INT          NOT NULL,  -- aankomsttijd van de trein
        TrainID     VARCHAR(50)  NOT NULL,
        Delay       INT          NOT NULL,
        Canceled    BIT          NOT NULL,
        LastUpdated DATETIME     NOT NULL DEFAULT GETDATE(),
        PRIMARY KEY (TrainID, StationKey, DateKey, TimeKey)
    );
END

GO

-- Non-negative value constraints (voorkomt negatieve waarden in de DWH)
-- Alles met ALTER TABLE zodat bestaande db makkelijk kan worden aangepast
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimDate_NonNegative')
BEGIN
    ALTER TABLE dbo.DimDate WITH CHECK ADD CONSTRAINT CK_DimDate_NonNegative CHECK (
        DateKey >= 0
        AND (DayOfMonth IS NULL OR DayOfMonth >= 0)
        AND (DayOfWeek IS NULL OR DayOfWeek >= 0)
        AND (DayOfWeekInMonth IS NULL OR DayOfWeekInMonth >= 0)
        AND (DayOfWeekInYear IS NULL OR DayOfWeekInYear >= 0)
        AND (DayOfQuarter IS NULL OR DayOfQuarter >= 0)
        AND (DayOfYear IS NULL OR DayOfYear >= 0)
        AND (WeekOfMonth IS NULL OR WeekOfMonth >= 0)
        AND (WeekOfQuarter IS NULL OR WeekOfQuarter >= 0)
        AND (WeekOfYear IS NULL OR WeekOfYear >= 0)
        AND (Month IS NULL OR Month >= 0)
        AND (MonthOfQuarter IS NULL OR MonthOfQuarter >= 0)
        AND (Quarter IS NULL OR Quarter >= 0)
        AND (Year IS NULL OR Year >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimTime_NonNegative')
BEGIN
    ALTER TABLE dbo.DimTime WITH CHECK ADD CONSTRAINT CK_DimTime_NonNegative CHECK (
        TimeKey >= 0
        AND (Hour IS NULL OR Hour >= 0)
        AND (Minute IS NULL OR Minute >= 0)
        AND (Hour12 IS NULL OR Hour12 >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimLocation_NonNegative')
BEGIN
    ALTER TABLE dbo.DimLocation WITH CHECK ADD CONSTRAINT CK_DimLocation_NonNegative CHECK (
        LocationKey >= 0
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimStaff_NonNegative')
BEGIN
    ALTER TABLE dbo.DimStaff WITH CHECK ADD CONSTRAINT CK_DimStaff_NonNegative CHECK (
        StaffKey >= 0
        AND (DepartementKey IS NULL OR DepartementKey >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimWorkerMobility_NonNegative')
BEGIN
    ALTER TABLE dbo.DimWorkerMobility WITH CHECK ADD CONSTRAINT CK_DimWorkerMobility_NonNegative CHECK (
        WorkerID >= 0
        AND (RecordDate IS NULL OR RecordDate >= 0)
        AND (TravelTime IS NULL OR TravelTime >= 0)
        AND (TravelDistance IS NULL OR TravelDistance >= 0)
        AND (TravelType IS NULL OR TravelType >= 0)
        AND (LocationKey IS NULL OR LocationKey >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimStation_NonNegative')
BEGIN
    ALTER TABLE dbo.DimStation WITH CHECK ADD CONSTRAINT CK_DimStation_NonNegative CHECK (
        StationKey >= 0
        AND (LocationKey IS NULL OR LocationKey >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimBlueBikeStation_NonNegative')
BEGIN
    ALTER TABLE dbo.DimBlueBikeStation WITH CHECK ADD CONSTRAINT CK_DimBlueBikeStation_NonNegative CHECK (
        BlueBikeStationKey >= 0
        AND LocationKey >= 0
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimCountingPoint_NonNegative')
BEGIN
    ALTER TABLE dbo.DimCountingPoint WITH CHECK ADD CONSTRAINT CK_DimCountingPoint_NonNegative CHECK (
        CountingPointID >= 0
        AND (DomainID IS NULL OR DomainID >= 0)
        AND (LocationKey IS NULL OR LocationKey >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimWeatherStation_NonNegative')
BEGIN
    ALTER TABLE dbo.DimWeatherStation WITH CHECK ADD CONSTRAINT CK_DimWeatherStation_NonNegative CHECK (
        WeatherStationKey >= 0
        AND (LocationKey IS NULL OR LocationKey >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimTransportType_NonNegative')
BEGIN
    ALTER TABLE dbo.DimTransportType WITH CHECK ADD CONSTRAINT CK_DimTransportType_NonNegative CHECK (
        TransportKey >= 0
        AND (CO2PerKM IS NULL OR CO2PerKM >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_DimDepartement_NonNegative')
BEGIN
    ALTER TABLE dbo.DimDepartement WITH CHECK ADD CONSTRAINT CK_DimDepartement_NonNegative CHECK (
        DepartementKey >= 0
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_FactCountings_NonNegative')
BEGIN
    ALTER TABLE dbo.FactCountings WITH CHECK ADD CONSTRAINT CK_FactCountings_NonNegative CHECK (
        CountingPointID >= 0
        AND DateKey >= 0
        AND (DirectionInCounts IS NULL OR DirectionInCounts >= 0)
        AND (DirectionOutCounts IS NULL OR DirectionOutCounts >= 0)
        AND (TotalCounts IS NULL OR TotalCounts >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_FactMeteo_NonNegative')
BEGIN
    ALTER TABLE dbo.FactMeteo WITH CHECK ADD CONSTRAINT CK_FactMeteo_NonNegative CHECK (
        DateKey >= 0
        AND WeatherStationKey >= 0
        AND (PrecipQuantity IS NULL OR PrecipQuantity >= 0)
        AND (WindSpeed10m IS NULL OR WindSpeed10m >= 0)
        AND (WindSpeedAvg30m IS NULL OR WindSpeedAvg30m >= 0)
        AND (WindGustsSpeed IS NULL OR WindGustsSpeed >= 0)
        AND (HumidityRelShelterAvg IS NULL OR HumidityRelShelterAvg >= 0)
        AND (Pressure IS NULL OR Pressure >= 0)
        AND (SunDuration IS NULL OR SunDuration >= 0)
        AND (ShortWaveFromSkyAvg IS NULL OR ShortWaveFromSkyAvg >= 0)
        AND (SunIntAvg IS NULL OR SunIntAvg >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_FactStaffCommute_NonNegative')
BEGIN
    ALTER TABLE dbo.FactStaffCommute WITH CHECK ADD CONSTRAINT CK_FactStaffCommute_NonNegative CHECK (
        (StaffKey IS NULL OR StaffKey >= 0)
        AND (DateKey IS NULL OR DateKey >= 0)
        AND (DistanceKM IS NULL OR DistanceKM >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_FactBlueBike_NonNegative')
BEGIN
    ALTER TABLE dbo.FactBlueBike WITH CHECK ADD CONSTRAINT CK_FactBlueBike_NonNegative CHECK (
        BlueBikeStationKey >= 0
        AND DateKey >= 0
        AND TimeKey >= 0
        AND TotalBikesAvailable >= 0
        AND EBikesAvailable >= 0
        AND BlueBikesAvailable >= 0
        AND MaxCapacity >= 0
        AND BikesDefect >= 0
        AND (BikesInUse IS NULL OR BikesInUse >= 0)
        AND (LinkedStationKey IS NULL OR LinkedStationKey >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_FactWorkerMobility_NonNegative')
BEGIN
    ALTER TABLE dbo.FactWorkerMobility WITH CHECK ADD CONSTRAINT CK_FactWorkerMobility_NonNegative CHECK (
        (WorkerID IS NULL OR WorkerID >= 0)
        AND (DateKey IS NULL OR DateKey >= 0)
        AND (TransportKey IS NULL OR TransportKey >= 0)
        AND (TotalEmission IS NULL OR TotalEmission >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_FactTrainArrival_NonNegative')
BEGIN
    ALTER TABLE dbo.FactTrainArrival WITH CHECK ADD CONSTRAINT CK_FactTrainArrival_NonNegative CHECK (
        StationKey >= 0
        AND DateKey >= 0
        AND StartTime >= 0
        AND EndTime >= 0
        AND AmountOfArrivals >= 0
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_FactDepartement_NonNegative')
BEGIN
    ALTER TABLE dbo.FactDepartement WITH CHECK ADD CONSTRAINT CK_FactDepartement_NonNegative CHECK (
        DateKey >= 0
        AND DepartementKey >= 0
        AND (AmountOfWorkers IS NULL OR AmountOfWorkers >= 0)
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_stg_FactTrainArrival_NonNegative')
BEGIN
    ALTER TABLE dbo.stg_FactTrainArrival WITH CHECK ADD CONSTRAINT CK_stg_FactTrainArrival_NonNegative CHECK (
        StationKey >= 0
        AND DateKey >= 0
        AND TimeKey >= 0
        AND Delay >= 0
    );
END
GO
