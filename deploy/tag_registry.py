# This file defines sets of tags for different deployment environments and is used by all apps to ensure consistent tagging of procedures and functions.

TAG_SETS = {
    "dev": ["core", "experimental", "diagnostic"],
    "qa": ["core", "stable"],
    "prod": ["core", "stable", "secure"]
}
