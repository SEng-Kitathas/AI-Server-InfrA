import os, json
print(json.dumps({
    'has_key': bool(os.environ.get('GITHOME_API_KEY')),
    'key_length': len(os.environ.get('GITHOME_API_KEY', '')),
    'host': os.environ.get('PCMMAD_BIND_HOST'),
    'port': os.environ.get('PCMMAD_BIND_PORT'),
    'browser_url': os.environ.get('PCMMAD_BROWSER_BRIDGE_URL'),
    'screenshot_dir_present': bool(os.environ.get('PCMMAD_BROWSER_SCREENSHOT_DIR')),
}))
