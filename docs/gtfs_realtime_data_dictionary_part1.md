# UTA GTFS Data Dictionary  
**Author:** Chase Powers – *Data Discovery & Description Lead*  
**Course:** CS6830 – Fundamentals of Data Engineering (Fall 2025)  

---

## Overview  
This document describes the structure and meaning of all GTFS tables included in the Utah Transit Authority (UTA) **Schedule Feed**.  
These tables form the core static data model used for routing, scheduling, and service analysis.  
All relationships are visually represented in the accompanying ER diagram.

---

## routes.txt  
Defines public transit routes (bus, rail, etc.).  

| Column | Type | Description |
|--------|------|-------------|
| route_id | varchar | Unique identifier for each route |
| agency_id | varchar | FK → agency.agency_id |
| route_short_name | varchar | Short name/number used publicly |
| route_long_name | varchar | Longer descriptive name |
| route_type | int | Transit mode (0=tram, 3=bus, etc.) |
| route_color | varchar | Hex display color |
| route_text_color | varchar | Text color for route display |

---

## trips.txt  
Defines individual scheduled vehicle trips.  

| Column | Type | Description |
|--------|------|-------------|
| trip_id | varchar | Unique trip identifier |
| route_id | varchar | FK → routes.route_id |
| service_id | varchar | FK → calendar.service_id |
| trip_headsign | varchar | Trip destination label |
| direction_id | int | Direction (0 or 1) |
| shape_id | varchar | FK → shapes.shape_id |

---

## stops.txt  
Defines physical stop or station locations.  

| Column | Type | Description |
|--------|------|-------------|
| stop_id | varchar | Unique stop identifier |
| stop_name | varchar | Stop name |
| stop_lat | float | Latitude |
| stop_lon | float | Longitude |
| location_type | int | 0=stop, 1=station |

---

## stop_times.txt  
Defines every scheduled stop for every trip.  

| Column | Type | Description |
|--------|------|-------------|
| trip_id | varchar | FK → trips.trip_id |
| stop_id | varchar | FK → stops.stop_id |
| arrival_time | varchar | Scheduled arrival |
| departure_time | varchar | Scheduled departure |
| stop_sequence | int | Order of stops in trip |

---

## calendar.txt  
Defines weekly recurring service.  

| Column | Type | Description |
|--------|------|-------------|
| service_id | varchar | Unique identifier for service pattern |
| monday–sunday | bool | 1 if service runs on that day |
| start_date | date | Start date |
| end_date | date | End date |

---

## calendar_dates.txt  
Defines special schedule adjustments.  

| Column | Type | Description |
|--------|------|-------------|
| service_id | varchar | FK → calendar.service_id |
| date | date | Special service date |
| exception_type | int | 1=added, 2=removed |

---

## shapes.txt  
Defines geographic route geometry.  

| Column | Type | Description |
|--------|------|-------------|
| shape_id | varchar | Unique shape identifier |
| shape_pt_lat | float | Shape point latitude |
| shape_pt_lon | float | Shape point longitude |
| shape_pt_sequence | int | Order of shape points |
| shape_dist_traveled | float | Cumulative distance |

---

## feed_info.txt  
Provides metadata about the feed.  

| Column | Type | Description |
|--------|------|-------------|
| feed_publisher_name | varchar | Publishing agency |
| feed_publisher_url | varchar | Publisher URL |
| feed_lang | varchar | Dataset language |
| feed_start_date | date | Validity start |
| feed_end_date | date | Validity end |
| feed_version | varchar | Feed version |

---

## Relationship Summary  
- routes.route_id → trips.route_id  
- trips.trip_id → stop_times.trip_id  
- stop_times.stop_id → stops.stop_id  
- trips.service_id → calendar.service_id  
- calendar.service_id → calendar_dates.service_id  
- trips.shape_id → shapes.shape_id  

---

## Summary  
This data dictionary serves as a complete reference for UTA’s GTFS Schedule dataset.  
It complements the ER diagram and the data discovery report by defining every table, column, and key relationship used in the system.