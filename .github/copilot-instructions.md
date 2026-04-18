# PSARC Library - AI Agent Instructions

## Project Overview

Web application for browsing and managing Rocksmith DLC libraries by parsing `.psarc` files.
Built on `python-template-server` (FastAPI base class) with SQLModel database, automatic initialization, manual sync workflow, and comprehensive error tracking.
Provides REST API + static web UI for exploring song metadata from Rocksmith 2014 DLC files.

## Architecture & Key Components

### Application Workflow

1. **Server Startup**: Auto-initializes database by scanning DLC folder and parsing all `.psarc` files
2. **Manual Sync**: User triggers resync via `/api/sync` endpoint to detect new files
3. **File Validation**: `/api/validate` endpoint allows pre-validation of files before adding to DLC folder
4. **Error Tracking**: Failed parsing attempts recorded in `failed_psarc` table with full error details
5. **Auto-Cleanup**: Sync operation removes failed entries for files no longer in DLC folder

### Server Implementation

- Entry: `main.py:run()` → instantiates `PsarcLibraryServer` (subclass of `TemplateServer`) → calls `.run()`
- `PsarcLibraryServer.__init__()` initializes `DatabaseManager` with DLC folder path from environment
- `DatabaseManager.__init__()` auto-scans DLC folder and populates database on first startup
- **Extensibility**: Inherits auth, rate limiting, CORS, security headers from `TemplateServer`

- **Extensibility**: Inherits auth, rate limiting, CORS, security headers from `TemplateServer`

### Database Architecture

**SQLModel with SQLite** - 4 tables with relationships:

1. **psarc_data** (PsarcDataDB):
   - Fields: id, filename, iteration_version, model_name, is_in_game
   - One-to-many with song_data (cascade delete)
   - Indexed by filename for duplicate detection

2. **song_data** (SongDataDB):
   - Fields: id, psarc_data_id, tuning_id, title, artist, album, year, length, tempo, dlc, dlc_key
   - Foreign keys to psarc_data and tuning
   - Indexed by title, artist, album, year, dlc for search performance

3. **tuning** (TuningDB):
   - Fields: id, root, type
   - Shared tuning entries (Standard E, Drop D, Custom)
   - One-to-many with song_data

4. **failed_psarc** (FailedPsarcDB):
   - Fields: id, filename, filepath, error_type, error_message, timestamp, file_size, raw_data
   - Tracks parsing failures with full tracebacks
   - Indexed by filename for cleanup operations
   - Auto-cleaned during sync if file no longer exists

**Database Operations:**
- `_initialize_database()`: Scans DLC folder on startup, adds all `.psarc` files
- `_process_psarc_file()`: Parses single file with try/except, calls `_record_failure()` on error
- `_record_failure()`: Upserts failed entry with error type, message, timestamp, traceback
- `_get_or_create_tuning()`: Deduplicates tunings to avoid redundant entries
- `add_psarc_data()`: Transactional insert of PSARC + songs + tunings
- `sync_psarc_directory()`: Rescans folder, adds new files, cleans up missing failed entries

### Caching System

**Implementation**: `cachetools.TTLCache` with decorator pattern for automatic invalidation

- **Cache Configuration**: 5-minute TTL, 1000 max items, stored on `DatabaseManager._cache`
- **Cached Methods** (read-heavy operations):
  - `get_all_psarc_data(skip, limit)` - list PSARC files with pagination
  - `search_songs(title, artist, album, year, skip, limit)` - song search queries
  - `count_psarc_data()` - total PSARC file count
  - `count_songs()` - total song count
  - `get_all_failed_psarc(skip, limit)` - list failed entries
  - `count_failed_psarc()` - failed entry count

- **Cache Invalidation** (write operations call `_clear_cache()`):
  - `add_psarc_data()` - clears after adding new PSARC + songs
  - `sync_psarc_directory()` - clears after sync completion
  - `_record_failure()` - clears after recording new failure
  - `delete_failed_psarc_by_filename()` - clears after deletion

- **Cache Decorator**: `@cache_method` wrapper generates keys from function name + args/kwargs
- **Debug Logging**: Cache hits/misses logged at DEBUG level

### Configuration System

- `config.json` loaded via `TemplateServer.load_config()` method, validated as `PsarcLibraryServerConfig`
- Extends `TemplateServerConfig` with `db` field for `PsarcDatabaseConfig`
- Database config: `db_directory` (default: "data/"), `db_filename` (default: "psarc_library.db")
- Environment variables: `HOST`, `PORT`, `API_TOKEN_HASH`, `PSARC_DIR` (required - DLC folder path)
- PSARC decryption: `PSARC_TOC_DECRYPTION_KEY` environment variable for encrypted archives
- Logging: Rotating file handler in `logs/`, 10MB per file, 5 backups

### API Endpoints

All endpoints under `/api` prefix, require `X-API-Key` header (except `/health`):

**PSARC Data (Read-Only)**:
- `GET /api/psarc/{psarc_id}` - Get single PSARC entry by ID
  - Response: `GetPsarcDataResponse` with `PsarcData` object
  - 404 if not found
- `GET /api/psarc?skip=0&limit=100` - List all PSARC entries (paginated)
  - Response: `ListPsarcDataResponse` with array of `PsarcData`, total count
  - Cached (5min TTL)

**Sync and Validation**:
- `POST /api/sync` - Rescan DLC folder and add new files
  - Response: `SyncResponse` with stats (processed, added, failed, skipped, cleaned)
  - Clears cache after completion
  - Auto-removes failed entries for missing files
- `POST /api/validate` - Upload and validate PSARC file (multipart/form-data)
  - Requires `.psarc` file upload
  - Response: `ValidatePsarcResponse` with validation status, parsed data or error
  - Does NOT add to database
  - Temporary file cleaned up after validation

**Failed Entries**:
- `GET /api/failures?skip=0&limit=100` - List failed parsing attempts (paginated)
  - Response: `ListFailedPsarcResponse` with array of `FailedPsarcEntry`, total count
  - Cached (5min TTL)

**Song Search**:
- `GET /api/songs/search?title=...&artist=...&album=...&year=2024&skip=0&limit=100`
  - Partial match on title/artist/album, exact match on year
  - Response: `SearchSongsResponse` with array of `SongData`
  - Cached (5min TTL)

**Statistics**:
- `GET /api/stats` - Database statistics
  - Response: `StatsResponse` with total_psarc_files, total_songs, total_failed_files
  - Cached (5min TTL)

### Static Web UI

**Location**: `static/index.html` (dark theme, responsive design)

**Features**:
- API key storage (localStorage)
- Dashboard: Stats display (PSARC files, songs, failed entries)
- Sync button: Trigger manual resync with result notification
- PSARC browser: Paginated list with song details expansion
- Song search: Filter by title/artist/album/year
- Failed entries viewer: Browse parsing errors with full details
- File validation: Upload `.psarc` file for pre-validation before DLC folder addition

**No Authentication Required**: Static files served without API key verification


**No Authentication Required**: Static files served without API key verification

### Authentication Architecture (Inherited from TemplateServer)

- **Token Generation**: `uv run generate-new-token` creates secure token + SHA-256 hash
- **Hash Storage**: Only hash stored in `.env` (API_TOKEN_HASH), raw token shown once
- **Verification Flow**: Request → `_verify_api_key()` dependency → hash comparison
- **Health Endpoint**: `/api/health` does NOT require authentication
- Header: `X-API-Key` (all PSARC Library endpoints require authentication)

### CORS Middleware (Inherited from TemplateServer)

- Optional cross-origin resource sharing support
- Controlled by `config.cors.enabled` flag (disabled by default)
- Configurable origins, methods, headers, credentials
- Typical use: Allow frontend applications on different domains to access API

### Rate Limiting (Inherited from TemplateServer)

- Uses `slowapi` with configurable storage (in-memory/Redis/Memcached)
- Applied via `_limit_route()` wrapper when `config.rate_limit.enabled=true`
- All PSARC Library endpoints marked as `limited=True`
- Format: `"100/minute"` (supports /second, /minute, /hour)

### Observability Stack

- **Logging**: Dual output (console + rotating file), 10MB per file, 5 backups in `logs/`
- **Request Tracking**: `RequestLoggingMiddleware` logs all requests with client IP
- **Cache Performance**: Cache hits/misses logged at DEBUG level
- **Error Details**: Full tracebacks stored in failed_psarc table with timestamps

## Developer Workflows

### Essential Commands

```powershell
# Setup (first time)
uv sync                          # Install dependencies
uv run generate-new-token        # Generate API key, save hash to .env

# Development
uv run psarc-library             # Start server (https://localhost:443/api)
uv run -m pytest                 # Run tests with coverage
uv run -m mypy .                 # Type checking
uv run -m ruff check .           # Linting

# Docker Development
docker compose up --build -d     # Build + start all services
docker compose logs -f psarc-library  # View logs
docker compose down              # Stop and remove containers
```

### Environment Setup

**Required Environment Variables**:
- `PSARC_DIR` - Path to DLC folder containing `.psarc` files (required)
- `API_TOKEN_HASH` - SHA-256 hash of API token (auto-generated if missing)

**Optional Environment Variables**:
- `HOST` - Server host (default: localhost)
- `PORT` - Server port (default: 443)
- `PSARC_TOC_DECRYPTION_KEY` - Decryption key for encrypted PSARC archives

### Testing Patterns

- **Fixtures**: All tests use `conftest.py` fixtures for models
- **Model Fixtures**: `mock_tuning_dict_*`, `mock_tuning_*`, `mock_song_data_entry`, `mock_psarc_manifest`
- **Server Mocking**: `mock_server` fixture with auth disabled for testing
- **Config Mocking**: `mock_psarc_library_server_config` fixture
- **Pattern**: Unit tests per module (test\_\*.py) + integration tests (test_server.py)

### Docker Multi-Stage Build

- **Stage 1 (backend-builder)**: Uses `uv` to build wheel with pyproject.toml, source code
- **Stage 2 (runtime)**: Installs wheel, copies configuration, static files, `.here` marker
- **Startup Script**: `/app/start.sh` generates token if missing, starts server
- **Environment Variables**:
  - `HOST`, `PORT`, `API_TOKEN_HASH` (auto-generated if missing)
  - `PSARC_DIR=/psarc` (container path where host DLC folder is mounted)
  - `PSARC_TOC_DECRYPTION_KEY` (optional, for encrypted archives)
- **Volume Mounts**:
  - `${PSARC_DIR}:/psarc:ro` - Host DLC folder mounted read-only (PSARC_DIR from host .env)
  - `./data:/app/data` - Database persistence (SQLite file stored here)
  - `./.env:/app/.env` - Environment variables
  - `certs:/app/certs` - SSL certificates (named volume)
  - `logs:/app/logs` - Application logs (named volume)
- **Health Check**: Python urllib request to `/api/health` (no auth required)

## Project-Specific Conventions

### Code Organization

- **Server**: `server.py` - `PsarcLibraryServer` class with endpoint handlers
- **Database**: `database.py` - `DatabaseManager` class with SQLModel operations + caching
- **PSARC Parser**: `psarc.py` - `parse_psarc()` function for binary file parsing
- **Models**: `models.py` - Pydantic models for API responses + SQLModel database models
- **Constants**: `constants.py` - Environment variable names, magic numbers
- **Static Files**: `static/` directory for web UI

### Database Patterns

- **Initialization**: Auto-scan DLC folder on first startup
- **Sync Operations**: Manual trigger via API endpoint, not automatic file watching
- **Error Recording**: All parsing failures stored with full context (type, message, traceback, file size)
- **Cache Invalidation**: Write operations clear cache to ensure consistency
- **Deduplication**: Tunings shared across songs to reduce redundancy
- **Cascading Deletes**: Deleting PSARC removes associated songs automatically

### Caching Strategy

- **Cache Decorator**: `@cache_method` on read-heavy methods
- **TTL**: 5 minutes (CACHE_TTL constant)
- **Max Size**: 1000 items (CACHE_MAXSIZE constant)
- **Key Generation**: Function name + args + kwargs
- **Invalidation**: `_clear_cache()` called after write operations
- **Debug Mode**: Enable DEBUG logging to see cache hits/misses

### API Design

- **Prefix**: All routes under `/api` (inherited from TemplateServer)
- **Authentication**: All endpoints require `X-API-Key` header except `/health`
- **Response Models**: All endpoints return Pydantic models with code/message/timestamp
- **Pagination**: `skip` and `limit` query params for list endpoints (default: 0, 100)
- **Error Handling**: Custom HTTPException with appropriate status codes (404, 400)
- **File Upload**: `multipart/form-data` for PSARC validation endpoint

### Logging Format

- Format: `[DD/MM/YYYY | HH:MM:SS] (LEVEL) module: message`
- Request logs: `"Request: GET /api/stats from 192.168.1.1"`
- Database ops: `"Adding PSARC data: filename.psarc"`, `"Retrieved 10 songs"`
- Cache logs: `"Cache hit for get_all_psarc_data:(0,):{100}"`
- Failures: `"Recording failure for PSARC file: filename.psarc - ParseError"`

## Development Constraints

### Testing Requirements

- Use fixtures for consistent test data (tunings, songs, manifests)
- Mock authentication for integration tests (`fake_verify_api_key`)
- Test async endpoints with proper FastAPI TestClient
- Mock `DatabaseManager` when testing endpoint logic

### CI/CD Validation

All PRs must pass:

**CI Workflow (ci.yml)**:
1. `validate-pyproject` - pyproject.toml schema validation
2. `ruff` - linting (120 char line length)
3. `mypy` - 100% type coverage (strict mode)
4. `pytest` - test suite with coverage
5. `bandit` - security check
6. `pip-audit` - dependency vulnerability scan
7. `version-check` - version consistency

**Build Workflow (build.yml)**:
1. `build-wheel` - Create Python wheel package
2. `verify-structure` - Verify package structure

**Docker Workflow (docker.yml)**:
1. `build` - Build and test Docker image

## Quick Reference

### Key Files

- `server.py` - PsarcLibraryServer class with API endpoints
- `database.py` - DatabaseManager with SQLModel operations and caching
- `psarc.py` - PSARC file parser (binary format, encryption support)
- `models.py` - Pydantic response models + SQLModel database models
- `constants.py` - Environment variable names, cache config
- `main.py` - Entry point, server instantiation
- `static/index.html` - Web UI for browsing library
- `docker-compose.yml` - Container stack with volume mounts

### Environment Variables

- `PSARC_DIR` - Path to DLC folder (required)
- `HOST` - Server host (default: localhost)
- `PORT` - Server port (default: 443)
- `API_TOKEN_HASH` - SHA-256 hash of API token (auto-generated if not provided)
- `PSARC_TOC_DECRYPTION_KEY` - Decryption key for PSARC files (optional)

### Configuration Files

- `configuration/config.json` - Server configuration (rate limiting, CORS, database, etc.)
- `.env.example` - Template for environment variables
- `.env` - Environment variables (auto-created by generate-new-token or Docker startup)
- **Docker**: Startup script auto-generates token if missing
