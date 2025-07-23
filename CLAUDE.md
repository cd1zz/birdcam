# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BirdCam is a distributed wildlife detection system with a two-system architecture:
- **Raspberry Pi**: Camera capture with motion detection (`pi_capture/`)
- **AI Processing Server**: YOLO-based detection and web interface (`ai_processor/`, `web/`)

## Development Commands

### Frontend (Web UI)
```bash
cd web-ui
npm install                # Install dependencies
npm run dev               # Start development server
npm run build             # Production build
npm run lint              # Run ESLint
npm run test              # Unit tests (Vitest)
npm run test:coverage     # Tests with coverage
npm run test:e2e          # E2E tests (Playwright)
npm run test:all          # All tests
```

### Backend (Python)
```bash
# Virtual environment is in project root
source .venv/bin/activate

# Install dependencies
pip install -r requirements.capture.txt    # For Pi system
pip install -r requirements.processor.txt  # For AI server

# Run tests
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest tests/test_api.py  # Run specific test file

# Run services (for testing/development)
python pi_capture/main.py      # Run Pi capture service
python ai_processor/main.py    # Run AI processor service

# Service management (ask user to run these with sudo)
# sudo systemctl start/stop/restart ai-processor.service
# sudo systemctl start/stop/restart pi-capture.service
# journalctl -u ai-processor.service -f
```

## Architecture

### Backend Structure
- **Two-system design**: Pi captures video, server processes with AI
- **Flask-based**: Both systems use Flask for web APIs
- **Database**: SQLite with repository pattern (`database/`)
- **Services layer**: Business logic in `services/`
- **Authentication**: JWT-based with role support (admin/viewer)
- **Email**: SMTP integration for user registration

### Frontend Structure
- **React 19 + TypeScript**: Modern React with Vite
- **State Management**: React Query for server state
- **Styling**: Tailwind CSS
- **Testing**: Vitest (unit), Playwright (E2E)
- **Components**: Camera feeds, detection galleries, admin panel

### Key Directories
- `pi_capture/`: Raspberry Pi camera system
- `ai_processor/`: YOLO detection and video processing
- `web/`: Flask API routes and authentication
- `web-ui/`: React frontend application
- `database/`: SQLite repositories and migrations
- `services/`: Business logic (AI, camera, auth, email)
- `core/`: Shared models and data structures
- `config/`: Configuration and examples
- `systemd/`: Linux service definitions

## Configuration

### Environment Files
- `.env.pi`: Pi camera settings (motion, cameras)
- `.env.processor`: AI server settings (detection, storage)
- `web-ui/.env`: Frontend API endpoints

### Critical Settings
- `SECRET_KEY`: Must match between Pi and Processor
- `CAPTURE_SERVER`: Pi's IP address (in processor config)
- `STORAGE_PATH`: Video storage location (needs space)

## Testing

### Running Specific Tests
```bash
# Python
pytest tests/test_api.py::test_specific_function
pytest -k "test_name_pattern"

# Frontend
npm run test -- UserProfile.test.tsx
npm run test:e2e -- --project=chromium
```

### Test Database
Tests use in-memory SQLite database. Fixtures in `tests/conftest.py`.

## Common Development Tasks

### Adding a New API Endpoint
1. Add route in `web/api/routes/`
2. Implement service logic in `services/`
3. Add repository methods if needed in `database/repositories/`
4. Update frontend API client if needed
5. Add tests for the endpoint

### Modifying AI Detection
1. Update `services/ai_model_manager.py` for model changes
2. Adjust detection logic in `ai_processor/main.py`
3. Update detection categories in `services/detection.py`

### Working with Camera Configuration
1. Camera configs are in `.env.pi`
2. Use `scripts/setup/pi_env_generator.py` for auto-detection
3. Camera 0 is active (motion detection), others are passive

## Security Considerations
- Admin operations restricted to local network IPs
- JWT tokens for authentication
- Email verification for new users
- Registration can be invitation-only, open, or disabled
- Secrets should never be committed (use .env files)

## Deployment
- Uses systemd services (see `systemd/` directory)
- Install scripts in `scripts/setup/`
- **Services**:
  - `pi-capture.service`: Runs on Raspberry Pi
  - `ai-processor.service`: Runs on AI processing server
- Frontend served statically by AI processor
- **Note**: Claude does not have sudo access. Ask the user to run sudo commands when needed (e.g., `sudo systemctl restart ai-processor.service`)

## Monitoring and Logs
- Logs go to journald/syslog
- Admin users can view logs in web UI
- Access logs track HTTP requests
- Motion detection logs include sensitivity data