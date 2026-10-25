from pydantic import BaseModel, ConfigDict


class CSVImportErrorItem(BaseModel):
    row: int
    field: str
    reason: str


class CSVImportResponse(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    dry_run: bool
    imported_count: int
    errors: list[CSVImportErrorItem]

    model_config = ConfigDict(from_attributes=True)
