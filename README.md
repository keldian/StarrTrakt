A set of Python scripts to sync your Starr PVR libraries with a Trakt.tv watchlist, to be used as a notification custom
script alongside the native Trakt Connection.

When a title is added to a library, this will also add it to your Trakt Watchlist. When a title is imported, this will
remove it from your Trakt Watchlist and the native Trakt connection will add it to your Trakt collection.

## Features

- Automatic Trakt.tv authentication with PIN-based setup
- Token refresh handling
- Detailed logging

## Setup

1. Clone this repository in a location accessible to your PVRs:

    ```bash
    git clone https://github.com/keldian/StarrTrakt.git /path/to/destination
    ```

1. Set up environment variables with your Trakt.tv API credentials:

   #### Docker Compose

      ```yaml
      services:
        radarr:
          environment:
            TRAKT_CLIENT_ID: "your_client_id"
            TRAKT_CLIENT_SECRET: "your_client_secret"
      ```

   #### Shell

   ```bash
   export TRAKT_CLIENT_ID="your_client_id"
   export TRAKT_CLIENT_SECRET="your_client_secret"
   ```

1. To get these credentials:

    1. Visit https://trakt.tv/oauth/applications
    1. Create a new application
    1. Set the Redirect URI to: `urn:ietf:wg:oauth:2.0:oob`
    1. Save and copy the Client ID and Client Secret

1. Make the scripts executable:
    ```bash
    chmod +x radarr_trakt.py sonarr_trakt.py
    ```

1. Run the test command to authenticate with Trakt:
    ```bash
    ./radarr_trakt.py test
    # or
    ./sonarr_trakt.py test
    ```

   Follow the prompts to authorize the application with your Trakt account.

## Radarr Setup

In Radarr, go to Settings → Connect → + → Custom Script

- Name: Trakt.tv Watchlist

  Supported triggers:

    - On File Import
    - On File Upgrade
    - On Movie Added
    - On Movie Delete

- Path: `/path/to/radarr_trakt.py`

## Sonarr Setup

In Sonarr, go to Settings → Connect → + → Custom Script and configure:

- Name: Trakt.tv Watchlist

  Supported triggers:

    - On File Import
    - On File Upgrade
    - On Import Complete
    - On Series Add
    - On Series Delete

- Path: `/path/to/sonarr_trakt.py`

## Usage

The scripts can automatically:

- Add titles to your Trakt watchlist when they are added to your library
- Remove titles from your Trakt watchlist when they are imported
- Remove titles from your Trakt watchlist when they are deleted from your library
- Create detailed logs in the `logs` directory

## Testing

You can test the connection to Trakt by running:

```bash
./radarr_trakt.py test
# or
./sonarr_trakt.py test
```

## Logs

Logs are stored in the `logs` directory:

- `radarr_trakt.log` - Radarr events and actions
- `sonarr_trakt.log` - Sonarr events and actions
- `common.log` - Shared authentication and API operations

## Troubleshooting

1. Check the logs in the `logs` directory for detailed error messages
2. Ensure your Trakt.tv API credentials are correctly set in environment variables
3. Try running the test command to verify authentication
4. Check file permissions - scripts need to be executable
5. Verify the paths in Radarr/Sonarr connection settings

## Development

The code is split into three main Python files:

- `common.py` - Shared functionality for Trakt.tv API interaction
- `radarr_trakt.py` - Radarr-specific event handling
- `sonarr_trakt.py` - Sonarr-specific event handling

## License

MIT License - See LICENSE file for details