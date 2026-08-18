from functools import (
    lru_cache,
)  # Import lru_cache so the application creates the settings object only once
from typing import (
    Literal,
)  # Import Literal so the allowed application environments can be restricted

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)  # Import Pydantic tools for typed environment-based configuration


class Settings(
    BaseSettings
):  # Define the central typed configuration used throughout the application
    app_name: str = (
        "JogoCanal"  # Define the application name used by FastAPI and its generated documentation
    )
    app_version: str = (
        "0.1.0"  # Define the current application version displayed by the API documentation
    )
    environment: Literal["development", "test", "production"] = (
        "development"  #  Restrict the application environment to known values
    )
    debug: bool = (
        False  # Disable FastAPI debug behaviour unless an environment explicitly enables it
    )

    model_config = SettingsConfigDict(  # Configure how Pydantic loads application settings
        env_file=".env",  # Allow local development settings to be loaded from a private .env file
        env_file_encoding="utf-8",  # Read the local environment file using UTF-8 encoding
        env_prefix="JOGOCANAL_",  # Prefix JogoCanal environment variables
        extra="ignore",  # Ignore unrelated environment variables
    )  # Finish the Pydantic settings configuration


@lru_cache  # Cache the result so repeated calls reuse one Settings instance
def get_settings() -> Settings:  # Create the shared application settings object
    return (
        Settings()
    )  # Load and validate settings from defaults, environment variables, and the optional .env file


settings = (
    get_settings()
)  # Expose the validated shared settings object to the rest of the application
