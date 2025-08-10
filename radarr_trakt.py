#!/usr/bin/env python3

import json
import os
import sys
from common import RadarrEventHandler

def main():
    try:
        handler = RadarrEventHandler()

        event_type = os.getenv("radarr_eventtype") or (sys.argv[1] if len(sys.argv) > 1 else "test")

        if len(sys.argv) > 2:
            event_data = json.loads(sys.argv[2])
        else:
            event_data = handler.build_event_data()
            
        success = handler.handle_event(event_type, event_data)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()