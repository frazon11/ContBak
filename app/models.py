from pydantic import BaseModel, Field

class BackupRequest(BaseModel):
    container_id: str = Field(min_length=1)
