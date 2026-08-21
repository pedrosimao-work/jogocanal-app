from sqlalchemy import MetaData  # Import MetaData for the exported Alembic metadata type

from app.db.base import Base  # Import the common declarative base containing the shared metadata
from app.models.admin_user import (
    AdminUser,
)  # Import the administrator model so SQLAlchemy registers its table
from app.models.channel import Channel  # Import the channel model so SQLAlchemy registers its table
from app.models.club import (
    Club,
    ClubAlias,
    ClubSourceMapping,
)  # Import canonical club and mapping models
from app.models.competition import Competition  # Import the canonical competition model
from app.models.league import (
    League,
    LeagueMembership,
)  # Import league and seasonal-membership models
from app.models.match import (
    Match,
    MatchChannel,
)  # Import match and many-to-many channel association models
from app.models.normalisation import (
    NormalisationCache,
)  # Import the persistent normalisation-cache model
from app.models.scrape import (
    ScrapeJob,
    ScrapeRun,
    ScrapeRunEvent,
)  # Import scraper execution and durable-job models

metadata: MetaData = Base.metadata  # Export the complete SQLAlchemy metadata collection for Alembic


__all__ = (  # Explicitly define the model objects exported by the app.models package
    "AdminUser",  # Export the administrator model
    "Channel",  # Export the channel model
    "Club",  # Export the canonical club model
    "ClubAlias",  # Export the club-alias model
    "ClubSourceMapping",  # Export the generic source-mapping model
    "Competition",  # Export the competition model
    "League",  # Export the league model
    "LeagueMembership",  # Export the seasonal league-membership model
    "Match",  # Export the match model
    "MatchChannel",  # Export the match/channel association model
    "NormalisationCache",  # Export the persistent normalisation-cache model
    "ScrapeJob",  # Export the durable scrape-job model
    "ScrapeRun",  # Export the scraper execution-summary model
    "ScrapeRunEvent",  # Export the structured scraper event model
    "metadata",  # Export the complete SQLAlchemy metadata collection
)  # Finish the explicit model exports
