# GTFS Realtime Data Dictionary

**Course:** CS6830 – Fundamentals of Data Engineering (Fall 2025)  
**Module:** Week 2 - Data Ingestion & Streaming  
**Author:** Jerico Radin  

---

## Overview

This document describes the schema and structure of the **GTFS Realtime** feed. Unlike the static schedule (CSV), this data is transmitted via **Protocol Buffers**. The "Tables" below represent the nested message objects defined in the standard `gtfs-realtime.proto` schema.

This dictionary maps the real-time stream structure and defines the relationships back to the Static GTFS Schedule.

---

## FeedMessage (Root)

The top-level container returned by every HTTP poll.



| Field | Type | Description |
| :--- | :--- | :--- |
| `header` | `FeedHeader` | Metadata about the feed (version, timestamp) |
| `entity` | `list<FeedEntity>` | A list of zero or more updates (trips, vehicles, alerts) |

---

## FeedHeader

Metadata describing the validity and freshness of the data payload.

| Field | Type | Description |
| :--- | :--- | :--- |
| `gtfs_realtime_version` | `string` | Version of the spec (e.g., "2.0") |
| `incrementality` | `enum` | `FULL_DATASET` (replace all) or `DIFFERENTIAL` (update changes only) |
| `timestamp` | `uint64` | POSIX time (seconds since epoch) of data generation. **Critical for latency checks.** |

---

## FeedEntity

A wrapper that holds exactly **one** specific type of update (Vehicle, Trip, or Alert).

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `string` | Unique identifier for this entity |
| `is_deleted` | `bool` | If true, the client should remove this entity from their view |
| `trip_update` | `TripUpdate` | (Optional) Real-time arrival/departure prediction |
| `vehicle` | `VehiclePosition` | (Optional) GPS location of a vehicle |
| `alert` | `Alert` | (Optional) Service disruption or notice |

---

## TripUpdate

Represents fluctuations in the schedule (delays, cancellations) for a specific trip.

| Field | Type | Description |
| :--- | :--- | :--- |
| `trip` | `TripDescriptor` | Identifies which trip this update affects |
| `vehicle` | `VehicleDescriptor` | Identifies the vehicle servicing this trip |
| `stop_time_update` | `list<StopTimeUpdate>` | Updates to arrival/departure times for future stops |
| `timestamp` | `uint64` | Time when this update was measured |
| `delay` | `int32` | Global delay for the trip (in seconds) if `stop_time_update` is missing |

---

## StopTimeUpdate

A sub-message within `TripUpdate` detailing schedule changes for a specific stop.

| Field | Type | Description |
| :--- | :--- | :--- |
| `stop_sequence` | `int32` | Order of the stop (Matches `stop_times.txt`) |
| `stop_id` | `string` | FK → `stops.txt` |
| `arrival` | `Event` | Predicted arrival (contains `delay`, `time`, `uncertainty`) |
| `departure` | `Event` | Predicted departure (contains `delay`, `time`, `uncertainty`) |
| `schedule_relationship` | `enum` | `SCHEDULED`, `SKIPPED`, or `NO_DATA` |

---

## VehiclePosition

Represents the physical location and status of a transit vehicle.

| Field | Type | Description |
| :--- | :--- | :--- |
| `trip` | `TripDescriptor` | The trip this vehicle is currently serving |
| `vehicle` | `VehicleDescriptor` | Physical identifier of the bus/train (e.g., Bus #405) |
| `position` | `Position` | Lat/Lon/Bearing/Speed data |
| `current_stop_sequence` | `int32` | The stop sequence index the vehicle is currently at or approaching |
| `current_status` | `enum` | `INCOMING_AT`, `STOPPED_AT`, or `IN_TRANSIT_TO` |
| `timestamp` | `uint64` | Time when the GPS reading was taken |

---

## Alert

Human-readable service alerts (accidents, construction, weather).

| Field | Type | Description |
| :--- | :--- | :--- |
| `active_period` | `list<TimeRange>` | Start and end times for the alert validity |
| `informed_entity` | `list<EntitySelector>` | Which route, stop, or agency is affected? |
| `cause` | `enum` | `STRIKE`, `MAINTENANCE`, `WEATHER`, `TECHNICAL_PROBLEM`, etc. |
| `effect` | `enum` | `NO_SERVICE`, `REDUCED_SERVICE`, `DETOUR`, etc. |
| `header_text` | `TranslatedString` | The headline of the alert |
| `description_text` | `TranslatedString` | The full body text of the alert |

---

## Cross-Reference: Realtime to Schedule

This section defines how the Realtime objects link to the Static CSV files (Foreign Keys).



| Realtime Object Field | Static CSV Table | Static CSV Column | Relationship Meaning |
| :--- | :--- | :--- | :--- |
| `TripUpdate.trip.trip_id` | `trips.txt` | `trip_id` | Links a live update to a scheduled trip |
| `TripUpdate.trip.route_id` | `routes.txt` | `route_id` | Links a live update to a specific route |
| `StopTimeUpdate.stop_id` | `stops.txt` | `stop_id` | Identifies which station is delayed |
| `VehiclePosition.trip.trip_id` | `trips.txt` | `trip_id` | Identifies which scheduled trip a vehicle is performing |

---

## Summary

This dictionary provides the schema definitions for the **Realtime Protobuf** feed.

* **Top Level:** `FeedMessage` contains all data.
* **Core Units:** `TripUpdate` (Time), `VehiclePosition` (Space), and `Alert` (Service).
* **Linking:** Data is joined to the Static Schedule primarily via `trip_id`, `route_id`, and `stop_id`.