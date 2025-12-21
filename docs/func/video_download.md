# Video Download

**Module:** `src/downloader.py` (CLI also accepts direct local file paths, bypassing download)

### Class: `YoutubeDownloader`

**Function:** `__init__(download_dir: str = "downloads")`
- **Purpose:** Initialize downloader
- **Inputs:** `download_dir` (optional, default: "downloads")
- **Outputs:** None (initializes instance)

**Function:** `validate_url(url: str) -> bool`
- **Purpose:** Validates YouTube URL format
- **Inputs:** `url: str` (YouTube URL)
- **Outputs:** `bool` (True if valid)

**Function:** `get_video_info(url: str) -> Optional[Dict[str, Any]]`
- **Purpose:** Gets video metadata without downloading
- **Inputs:** `url: str` (YouTube URL)
- **Outputs:** 
  ```python
  {
    'id': str,
    'title': str,
    'duration': int,  # seconds
    'uploader': str,
    'view_count': int,
    'description': str,
    'thumbnail': str
  }
  ```
- **Returns:** `None` if error

**Function:** `download(url: str, quality: str = "best", output_filename: Optional[str] = None) -> Optional[str]`
- **Purpose:** Downloads video from YouTube
- **Inputs:**
  - `url: str` (YouTube URL)
  - `quality: str` (optional: "best", "1080p", "720p", "480p", "360p")
  - `output_filename: str` (optional custom filename)
- **Outputs:** `str` (path to downloaded file) or `None` if error
- **Side Effects:** Creates file in `downloads/` directory

**Function:** `download_audio_only(url: str) -> Optional[str]`
- **Purpose:** Downloads only audio track as MP3
- **Inputs:** `url: str` (YouTube URL)
- **Outputs:** `str` (path to MP3 file) or `None` if error

**Helper:** `download_video(url: str, quality: str = "best") -> Optional[str>`
- **Purpose:** Convenience wrapper to instantiate `YoutubeDownloader` and call `download()`
- **Outputs:** Same as `download()`
