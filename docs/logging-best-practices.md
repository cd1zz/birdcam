# Logging Best Practices for BirdCam AI Processor

## Overview
This document outlines the logging standards and best practices for the BirdCam AI processor service.

## Logging Format Standards

### 1. Prefix Tags
All log messages should start with a bracketed tag indicating the log type:
- `[STATS]` - Statistics and progress information
- `[OK]` - Successful operations
- `[ERROR]` - Errors (output to stderr)
- `[WARNING]` - Warnings
- `[INFO]` - General information
- `[DEBUG]` - Debug information
- `[PROCESSING]` - Processing operations
- `[DETECTION]` - Detection results
- `[VIDEO]` - Video operations
- `[STORAGE]` - Storage operations
- `[CLEANUP]` - Cleanup operations
- `[AI]` - AI model operations
- `[RECEIVED]` - File reception
- `[CONFIG]` - Configuration
- `[SCHEDULER]` - Scheduler operations

### 2. Message Structure
- **Single-line format**: Use pipe-separated key-value pairs for structured data
  ```
  [TAG] Main message | key1=value1 | key2=value2
  ```
- **No indentation**: Avoid multi-line hierarchical output with spaces/tabs
- **Consistent spacing**: One space after the tag, no leading spaces

### 3. Progress Logging
Progress should be logged with consistent formatting:
```python
# Good
print(f"[STATS] Progress: {progress:.1f}% - {video.filename}")

# Bad (has leading spaces)
print(f"  [STATS] Progress: {progress:.1f}%")
```

### 4. Structured Data
Include relevant context as key-value pairs:
```python
# Good
print(f"[OK] Video processed | file={filename} | detections={count} | time={duration:.1f}s")

# Bad (unstructured)
print(f"[OK] Processed {filename}: {count} detections found in {duration:.1f}s")
```

### 5. Error Logging
Always include exception details when logging errors:
```python
try:
    # operation
except Exception as e:
    print(f"[ERROR] Failed to process video | file={filename} | error={str(e)} | type={type(e).__name__}", file=sys.stderr)
```

## Implementation Examples

### Before (Inconsistent)
```python
print(f"[STORAGE] Directory structure created:")
print(f"   [RECEIVED] Incoming: {self.incoming_dir}")
print(f"   [DETECTION] Detections: {self.detections_dir}")
print(f"  [STATS] Progress: {progress:.1f}%")  # Inconsistent spacing
```

### After (Consistent)
```python
print(f"[STORAGE] Directory structure created | incoming={self.incoming_dir} | detections={self.detections_dir}")
print(f"[STATS] Progress: {progress:.1f}% - {video.filename}")
```

## Benefits

1. **Parseable**: Structured format is easier to parse programmatically
2. **Consistent**: No formatting variations or alignment issues
3. **Searchable**: grep/search tools work better with consistent patterns
4. **Compact**: Single-line format reduces log volume
5. **Context-rich**: Key-value pairs provide clear context

## Migration Path

1. Fix immediate issues (remove leading spaces, tabs)
2. Convert multi-line hierarchical logs to single-line format
3. Add structured key-value pairs to existing logs
4. Consider using the `ProcessingLogger` utility class for new code

## Using ProcessingLogger

```python
from utils.logging_utils import ProcessingLogger

logger = ProcessingLogger()

# Progress logging
logger.progress(frame_number, total_frames, video_name="sample.mp4")

# Success logging
logger.ok("Video processed", file="sample.mp4", detections=5, time="2.3s")

# Error logging with exception
try:
    process_video()
except Exception as e:
    logger.error("Failed to process video", exception=e, file="sample.mp4")
```