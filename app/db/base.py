from sqlalchemy import (
    MetaData,
)  # Import MetaData so database constraint names can follow a predictable convention
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
)  # Import AsyncAttrs so ORM objects support asynchronous attribute loading
from sqlalchemy.orm import (
    DeclarativeBase,
)  # Import DeclarativeBase as the foundation for every ORM model

NAMING_CONVENTION: dict[str, str] = {  # Define stable names for database constraints and indexes
    "ix": "ix_%(column_0_label)s",  # Name automatically generated indexes consistently
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Name automatically generated unique constraints consistently
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Name check constraints using their table and explicit constraint name
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Name foreign-key constraints predictably
    "pk": "pk_%(table_name)s",  # Name primary-key constraints using their table name
}  # Finish the database naming convention


class Base(
    AsyncAttrs, DeclarativeBase
):  # Create the common declarative base inherited by every JogoCanal model
    metadata = MetaData(
        naming_convention=NAMING_CONVENTION
    )  # Attach the stable naming convention to all model metadata
