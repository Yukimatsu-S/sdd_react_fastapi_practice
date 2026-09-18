"""Value validation rules for Evolution Step fields."""


def validate_required_text(value: str, field_name: str) -> str:
    """Accept supplied text only when it contains a non-whitespace character.

    Args:
        value: Text submitted for a required Evolution Step field.
        field_name: Field name included in a validation error.

    Returns:
        str: Original submitted text without silently rewriting it.

    Raises:
        ValueError: If the submitted text is empty or whitespace-only.
    """
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def validate_change_description(value: str | None) -> str | None:
    """Accept an absent description or a supplied non-blank description.

    Args:
        value: Optional manual explanation of a proposed change.

    Returns:
        str | None: Original description, or None when the user clears it.

    Raises:
        ValueError: If a supplied description is empty or whitespace-only.
    """
    if value is None:
        return None
    return validate_required_text(value, "change_description")
