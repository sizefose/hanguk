from django.core.exceptions import ValidationError


def validate_spicy(value: int) -> None:
    if value < 0 or value > 5:
        raise ValidationError("Spicy must be between 0 and 5")
