-- Database Schema for Saltwater Intrusion Warning System
-- Target Database: PostgreSQL

CREATE TABLE IF NOT EXISTS Station (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    type VARCHAR(50) -- e.g., 'water_level', 'salinity'
);

CREATE TABLE IF NOT EXISTS WaterLevel (
    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES Station(id),
    recorded_at TIMESTAMP NOT NULL,
    water_level_m DOUBLE PRECISION,
    discharge_m3s DOUBLE PRECISION,
    system_version VARCHAR(50), -- For GloFAS version tracking
    UNIQUE(station_id, recorded_at)
);

CREATE TABLE IF NOT EXISTS Salinity (
    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES Station(id),
    recorded_at TIMESTAMP NOT NULL,
    conductivity_mS_per_m DOUBLE PRECISION,
    salinity_ppt DOUBLE PRECISION,
    UNIQUE(station_id, recorded_at)
);

CREATE TABLE IF NOT EXISTS Weather (
    id SERIAL PRIMARY KEY,
    station_id INTEGER REFERENCES Station(id),
    recorded_at TIMESTAMP NOT NULL,
    precipitation_sum DOUBLE PRECISION,
    temperature_mean DOUBLE PRECISION,
    evapotranspiration_sum DOUBLE PRECISION,
    UNIQUE(station_id, recorded_at)
);

-- Indexes for time-series queries
CREATE INDEX idx_waterlevel_time ON WaterLevel(recorded_at);
CREATE INDEX idx_salinity_time ON Salinity(recorded_at);
CREATE INDEX idx_weather_time ON Weather(recorded_at);
