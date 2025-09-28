from deploy.deploy_snowflake_app import VALID_TAGS
from deploy.tag_registry import TAG_SETS


def validate_tags_for_env(env_name: str, tags: list[str]) -> dict:
    allowed = set(TAG_SETS.get(env_name, []))
    valid = []
    invalid = []

    for tag in tags:
        if tag not in VALID_TAGS:
            invalid.append((tag, "not in VALID_TAGS"))
        elif tag not in allowed:
            invalid.append((tag, f"not allowed in {env_name}"))
        else:
            valid.append(tag)

    return {
        "valid": valid,
        "invalid": invalid,
        "narration": narrate_tag_validation(env_name, valid, invalid)
    }


def narrate_tag_validation(env_name, valid, invalid):
    lines = [f"🔍 Tag validation for `{env_name}`:"]
    if valid:
        lines.append(f"✅ Valid tags: {', '.join(valid)}")
    if invalid:
        for tag, reason in invalid:
            lines.append(f"❌ `{tag}` — {reason}")
    if not valid and not invalid:
        lines.append("⚠️ No tags provided.")
    return "\n".join(lines)
