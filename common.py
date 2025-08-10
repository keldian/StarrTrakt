#!/usr/bin/env python3

import json
import logging
import logging.handlers
import os
import time
import urllib.error
import urllib.request

# --- Trakt credentials from environment variables ---
TRAKT_CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
TRAKT_CLIENT_SECRET = os.environ.get("TRAKT_CLIENT_SECRET")
TRAKT_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"

def setup_logging(script_name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    tmp_dir = os.path.join(script_dir, "tmp")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)
    
    log_path = os.path.join(logs_dir, f"{script_name}.log")
    
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=2 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler]
        )
    except Exception as e:
        print(f"WARNING: Could not initialize file logging: {e}", flush=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
    return logging.getLogger(__name__)

logger = setup_logging("trakt_common")

def http_post(url, data, headers=None, timeout=10):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers or {},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8"), resp.status
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8"), e.code
    except Exception as e:
        raise

# --- TRAKT TOKEN MANAGEMENT ---

def get_token_file_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tmp_dir = os.path.join(script_dir, "tmp")
    return os.path.join(tmp_dir, "trakt_tokens.json")

def trakt_load_tokens():
    token_file = get_token_file_path()
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            return json.load(f)
    return None

def trakt_save_tokens(tokens):
    token_file = get_token_file_path()
    with open(token_file, "w") as f:
        json.dump(tokens, f, indent=2)

def trakt_is_token_expired(tokens):
    # Trakt "created_at" is in seconds since epoch, "expires_in" is in seconds
    # Add a buffer of 60 seconds
    if not tokens or "created_at" not in tokens or "expires_in" not in tokens:
        return True
    return time.time() > (tokens["created_at"] + tokens["expires_in"] - 60)

def trakt_post_json(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def trakt_get_new_tokens_with_pin(pin):
    payload = {
        "code": pin,
        "client_id": TRAKT_CLIENT_ID,
        "client_secret": TRAKT_CLIENT_SECRET,
        "redirect_uri": TRAKT_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    return trakt_post_json("https://api.trakt.tv/oauth/token", payload)

def trakt_refresh_tokens(tokens):
    payload = {
        "refresh_token": tokens["refresh_token"],
        "client_id": TRAKT_CLIENT_ID,
        "client_secret": TRAKT_CLIENT_SECRET,
        "redirect_uri": TRAKT_REDIRECT_URI,
        "grant_type": "refresh_token"
    }
    return trakt_post_json("https://api.trakt.tv/oauth/token", payload)

def trakt_get_valid_tokens():
    tokens = trakt_load_tokens()
    if tokens and not trakt_is_token_expired(tokens):
        return tokens
    if tokens and "refresh_token" in tokens:
        try:
            new_tokens = trakt_refresh_tokens(tokens)
            trakt_save_tokens(new_tokens)
            logger.info("Successfully refreshed Trakt access token.")
            return new_tokens
        except Exception as e:
            logger.warning(f"Trakt token refresh failed: {e}, falling back to PIN.")
    
    # PIN-based authentication
    print("To authorize this script with Trakt, visit:")
    print(f"https://trakt.tv/oauth/authorize?response_type=code&client_id={TRAKT_CLIENT_ID}&redirect_uri={TRAKT_REDIRECT_URI}")
    pin = input("Enter the PIN provided by Trakt: ").strip()
    if not pin:
        raise Exception("No PIN entered. Cannot authenticate Trakt.")
    new_tokens = trakt_get_new_tokens_with_pin(pin)
    trakt_save_tokens(new_tokens)
    logger.info("Successfully authorized Trakt with new PIN.")
    return new_tokens

def trakt_auth_headers():
    tokens = trakt_get_valid_tokens()
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_CLIENT_ID
    }

def trakt_headers():
    return trakt_auth_headers()

class TraktWatchlistConnection:
    def __init__(self):
        self.trakt_base_url = "https://api.trakt.tv"

    def _make_watchlist_request(self, action, media_type, item):
        """Handle common watchlist operations with retry logic"""
        key = "shows" if media_type == "series" else "movies"
        payload = {key: [item]}
        endpoint = "/sync/watchlist/remove" if action == "remove" else "/sync/watchlist"
        
        logger.info(f"{'Removing from' if action == 'remove' else 'Adding to'} watchlist: {payload}")
        
        for attempt in range(2):
            body, status = http_post(
                f"{self.trakt_base_url}{endpoint}",
                data=payload,
                headers=trakt_headers()
            )
            
            if status == 401 and attempt == 0:
                logger.info("Trakt token expired/unauthorized, refreshing and retrying...")
                trakt_get_valid_tokens()  # This will refresh if needed
                continue
                
            if status >= 400:
                raise Exception(f"Trakt watchlist operation failed: HTTP {status} {body}")
                
            return json.loads(body) if body else {}
            
        raise Exception("Failed to perform watchlist operation after token refresh")

    def add_to_watchlist(self, media_type, item):
        return self._make_watchlist_request("add", media_type, item)

    def remove_from_watchlist(self, media_type, item):
        return self._make_watchlist_request("remove", media_type, item)

    def test_connection(self):
        """Test Trakt authentication by calling /users/me"""
        try:
            logger.info("Testing Trakt authentication by calling /users/me")
            headers = trakt_headers()
            body, status = http_post(
                f"{self.trakt_base_url}/users/me",
                data=None,
                headers=headers
            )
            if status >= 400:
                raise Exception(f"HTTP {status}: {body}")
                
            data = json.loads(body)
            print("Trakt authentication successful. User:", data.get("username", "<unknown>"))
            logger.info("Trakt authentication test passed. User: %s", data.get("username", "<unknown>"))
            return True
        except Exception as e:
            logger.error(f"Trakt authentication test failed: {e}")
            print(f"Trakt authentication test failed: {e}")
            return False


def format_item(event_data):
    """Format event data into Trakt item format"""
    ids = {}
    if event_data.get('imdbId'):
        ids['imdb'] = event_data['imdbId']
    if event_data.get('tmdbId'):
        ids['tmdb'] = event_data['tmdbId']
    if event_data.get('tvdbId'):
        ids['tvdb'] = event_data['tvdbId']

    item = {"ids": ids}
    if event_data.get('title'):
        item["title"] = event_data['title']
    if event_data.get('year'):
        item["year"] = event_data['year']
    return item


class StarrEventHandler:
    """Base class for handling Starr application events"""
    
    def __init__(self, application_name, media_type, env_prefix):
        self.logger = setup_logging(f"{application_name}_trakt")
        self.conn = TraktWatchlistConnection()
        self.media_type = media_type
        self.env_prefix = env_prefix
        self.add_events = []  # Override in subclass
        self.remove_events = []  # Override in subclass

    def handle_event(self, event_type, event_data):
        """Handle Starr application events"""
        if not event_data:
            self.logger.warning("No valid event data found, skipping.")
            return False

        # Test event handling
        if event_type.lower() == "test":
            return self.conn.test_connection()
        
        try:
            item = format_item(event_data)
            event_type_lower = event_type.lower()
            
            # Handle different event types
            if event_type_lower in self.add_events:
                result = self.conn.add_to_watchlist(self.media_type, item)
                self.logger.info(f"Added {self.media_type} to watchlist: {result}")
                return True
                
            elif event_type_lower in self.remove_events:
                result = self.conn.remove_from_watchlist(self.media_type, item)
                self.logger.info(f"Removed {self.media_type} from watchlist: {result}")
                return True
                
            else:
                self.logger.info(f"No action for event type: {event_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to handle event: {e}")
            print(f"ERROR: Failed to handle event: {e}", flush=True)
            return False

    def build_event_data(self):
        """Build event data from environment variables"""
        title_var = f"{self.env_prefix}_title"
        if not os.getenv(title_var):
            return None
            
        data = {
            'title': os.getenv(title_var),
            'year': int(os.getenv(f"{self.env_prefix}_year", 0)) or None,
            'imdbId': os.getenv(f"{self.env_prefix}_imdbid"),
        }
        
        # Add numeric IDs
        for id_type in ['tmdbid', 'tvdbid']:
            env_key = f"{self.env_prefix}_{id_type}"
            if os.getenv(env_key):
                data[id_type] = int(os.getenv(env_key, 0)) or None
        
        return data

class SonarrEventHandler(StarrEventHandler):
    def __init__(self):
        super().__init__(
            application_name="sonarr",
            media_type="series",
            env_prefix="sonarr_series"
        )
        self.add_events = ["seriesadd"]
        self.remove_events = ["download", "seriesdelete"]

class RadarrEventHandler(StarrEventHandler):
    def __init__(self):
        super().__init__(
            application_name="radarr",
            media_type="movie",
            env_prefix="radarr_movie"
        )
        self.add_events = ["movieadded"]
        self.remove_events = ["download", "moviedelete"]