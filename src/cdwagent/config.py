"""CDWAgent configuration models"""

from pydantic import BaseModel, Field


# UCSF CDW deployment — fixed for the target environment. Users do not set these.
# An env var override is still honored (e.g. if the hostname ever changes) but is
# not expected in normal operation.
DEFAULT_CDW_SERVER = "QCDIDDWDB001.ucsfmedicalcenter.org"
DEFAULT_CDW_DATABASE = "CDW_NEW"


class ClinicalDBConfig(BaseModel):
    """Clinical Data Warehouse database configuration (SQL Server)"""
    server: str = Field(DEFAULT_CDW_SERVER, description="CDW database server host")
    database: str = Field(DEFAULT_CDW_DATABASE, description="CDW database name")
    username: str = Field(..., description="CDW database username")
    password: str = Field(..., description="CDW database password")


class CDWConfig(BaseModel):
    """Complete CDWAgent server configuration"""
    clinical_db: ClinicalDBConfig = Field(..., description="Clinical Data Warehouse configuration")
    namespace: str = Field("CDW", description="Tool namespace prefix")
    db_schema: str = Field("deid_uf", description="Database schema for table qualification (e.g., deid or deid_uf)")
    log_level: str = Field("INFO", description="Logging level")
