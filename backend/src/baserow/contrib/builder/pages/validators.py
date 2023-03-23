from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from baserow.contrib.builder.pages.constants import (
    PAGE_PATH_PARAM_PREFIX,
    PATH_PARAM_EXACT_MATCH_REGEX,
)
from baserow.contrib.builder.pages.types import PagePathParams


def path_validation(value: str):
    """
    Verifies that a path is semantically valid.

    :param value: The path that needs to be validated
    :raises ValidationError: If the path is not valid
    """

    if not value.startswith("/"):
        raise ValidationError("A path must start with a '/'")

    # We need to construct a full path for the URL validator to properly check if the
    # path is valid
    full_path = f"https://placeholder.com{value}"

    validator = URLValidator(message=f"The path {value} is semantically invalid")

    validator(full_path)


def path_params_validation(value: PagePathParams):
    """
    Verifies that all path params are semantically valid.

    :param value: The path params to check
    :raises ValidationError: If a path param is not semantically valid
    """

    for path_param in value.keys():
        full_path_param = f"{PAGE_PATH_PARAM_PREFIX}{path_param}"

        if not PATH_PARAM_EXACT_MATCH_REGEX.match(full_path_param):
            raise ValidationError(
                f"Path param {path_param} contains invalid characters"
            )
