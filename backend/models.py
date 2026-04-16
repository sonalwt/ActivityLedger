from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, func, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    activities = relationship("ActivityRecord", back_populates="user")


class ActivityRecord(Base):
    __tablename__ = "activity_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Multi-developer support (stateless)
    developer_id = Column(String, index=True, nullable=True)  # String identifier, no FK

    application_name = Column(String, index=True)
    window_title = Column(Text)
    url = Column(Text, nullable=True)  # For browser activities
    file_path = Column(Text, nullable=True)  # For IDE/editor files
    database_connection = Column(String, nullable=True)  # For database tools
    specific_process = Column(String, nullable=True)  # For system processes
    detailed_activity = Column(Text, nullable=True)  # Enhanced description
    category = Column(String, index=True)  # browser, ide, productivity, etc.
    subcategory = Column(String, nullable=True)
    category_confidence = Column(Float, nullable=True)
    duration = Column(Float)  # Duration in seconds
    timestamp = Column(DateTime(timezone=True))  # Original activity timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    activity_data = Column(Text, nullable=True)  # Extra activity metadata

    # Project information fields
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)  # FK to projects table
    project_name = Column(String, index=True, nullable=True)  # Extracted project name
    project_type = Column(String, nullable=True)  # Development, Server Management, etc.
    project_file = Column(String, nullable=True)  # File or activity within project

    project = relationship("Project", backref="activities")

    user = relationship("User", back_populates="activities")

    __table_args__ = (
        UniqueConstraint('developer_id', 'timestamp', 'application_name', 'duration',
                         name='uq_activity_dedup'),
        Index('idx_activity_dedup', 'developer_id', 'timestamp', 'application_name', 'duration'),
        # Fast lookup index for dashboard queries (developer + date range)
        Index('idx_dev_timestamp', 'developer_id', 'timestamp'),
    )


class AFKRecord(Base):
    """Stores AFK watcher data separately — tracks active vs away time."""
    __tablename__ = "afk_records"

    id = Column(Integer, primary_key=True, index=True)
    developer_id = Column(String, index=True, nullable=False)
    status = Column(String(20))  # "not-afk" or "afk"
    duration = Column(Float)  # Duration in seconds
    timestamp = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('developer_id', 'timestamp', 'duration',
                         name='uq_afk_dedup'),
        Index('idx_afk_dev_timestamp', 'developer_id', 'timestamp'),
    )


# Optional: Developer model for future use (not required for stateless system)
class Developer(Base):
    __tablename__ = "developers"
    
    id = Column(Integer, primary_key=True, index=True)
    developer_id = Column(String, unique=True, index=True)  # Unique identifier
    name = Column(String)
    email = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    hourly_cost = Column(Float, nullable=True, default=0)  # Cost per hour in currency
    api_token = Column(String, unique=True, nullable=True)  # Optional for future use
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_sync = Column(DateTime(timezone=True), nullable=True)
    
    # Add relationship to activity records
    # Disable this relationship as it's causing type mismatch errors
    # activities = relationship("ActivityRecord", 
    #                         primaryjoin="Developer.developer_id==ActivityRecord.developer_id",
    #                         foreign_keys="ActivityRecord.developer_id",
    #                         backref="developer")


# Enhanced model for dynamic developer discovery
class DiscoveredDeveloper(Base):
    """Cache discovered developers to avoid repeated network scans"""
    __tablename__ = 'discovered_developers_enhanced'
    
    id = Column(String(255), primary_key=True)  # developer_id
    name = Column(String(255))
    host = Column(String(255))
    port = Column(Integer)
    hostname = Column(String(255))
    device_id = Column(String(255))
    description = Column(Text)
    version = Column(String(50))
    bucket_count = Column(Integer, default=0)
    activity_count = Column(Integer, default=0)
    
    # Status tracking
    status = Column(String(50), default='unknown')  # online, offline, database_only
    last_seen = Column(DateTime(timezone=True))
    last_checked = Column(DateTime(timezone=True))
    
    # Discovery metadata
    source = Column(String(50))  # network, local, database
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    """Stores valid project names for the Project Time Analysis dropdown"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)  # Project name
    description = Column(Text, nullable=True)
    total_cost = Column(Float, nullable=True, default=0)  # Total project cost/budget
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Holiday(Base):
    """Stores holidays for highlighting in analytics charts"""
    __tablename__ = 'holidays'

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    holiday_type = Column(String(50), default='national')  # national, optional, company
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('date', 'name', name='uq_holiday_date_name'),
    )
