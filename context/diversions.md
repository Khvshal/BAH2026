# POLARIS Development Diversions Log

This document logs all architectural and technical decisions made during the POLARIS platform implementation that deviate from the initial `POLARIS_Blueprint.md` specification.

---

## 1. Task Queue: FastAPI BackgroundTasks instead of Redis + Celery
* **Blueprint Specification**: Section 3.2 calls for Celery + Redis for managing asynchronous processing tasks.
* **Implemented Approach**: We utilized FastAPI's built-in `BackgroundTasks` and connection broadcasting.
* **Rationale**: Since the processing engines complete dem and radar calibration within a reasonable timeframe, setting up, configuring, and running Redis and Celery servers locally on Windows introduces significant environment setup overhead without any benefit for the hackathon deployment. Native background workers keep the server self-contained and highly reliable.

## 2. 2D Base64 Mapping instead of CesiumJS 3D Terrain
* **Blueprint Specification**: Section 3.2 and Section 7 call for 3D CesiumJS/Resium integration for terrain, hazard, and ice mapping.
* **Implemented Approach**: We utilized high-performance 2D base64 PNG rendering generated on-the-fly by the backend using Matplotlib colormaps, layered directly in React.
* **Rationale**: Embedding CesiumJS requires fetching heavy global assets, configuring tokens, and rendering large polygon datasets, which increases frontend bundle sizes and introduces high render latency. 2D base64 mapping renders under 100ms and guarantees high frame-rates and accurate color scaling.

## 3. Hybrid Storage Architecture
* **Blueprint Specification**: Section 3.2 specifies storing maps in the database/tile server.
* **Implemented Approach**: We implemented a hybrid storage layer where heavy binary artifacts (`.npy` arrays, images, processed maps) remain cached in `backend/engines/output`, while PostgreSQL with PostGIS stores all structured analytical metadata, craters, landing candidate rankings, rover traverse paths, and volume estimates.
* **Rationale**: Storing raw multi-megabyte numpy arrays inside database blobs causes severe database bloat and slow retrieval times. The hybrid approach combines the quick file-read speed for image mapping with the indexing and spatial querying capabilities of PostgreSQL and PostGIS.
