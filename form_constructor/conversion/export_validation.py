from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExportDiagnostic:
    stage: str
    message: str
    line: int | None = None
    pattern: str | None = None
    entity_id: str | None = None
    entity_type: str | None = None
    details: dict[str, object] = field(default_factory=dict)

    def format_message(self) -> str:
        parts = [self.message]
        if self.line is not None:
            parts.append(f"line {self.line}")
        if self.pattern:
            parts.append(f"pattern: {self.pattern}")
        if self.entity_id:
            parts.append(f"entity_id: {self.entity_id}")
        if self.entity_type:
            parts.append(f"entity_type: {self.entity_type}")
        return " | ".join(parts)


class ExportDiagnosticError(ValueError):
    def __init__(self, diagnostic: ExportDiagnostic) -> None:
        super().__init__(diagnostic.format_message())
        self.diagnostic = diagnostic


class ExportValidator:
    def validate_python_syntax(self, code: str, *, filename: str = "<generated_export>") -> None:
        try:
            ast.parse(code, filename=filename)
        except SyntaxError as error:
            diagnostic = ExportDiagnostic(
                stage="validate_python_syntax",
                message="Generated Python is not valid syntax.",
                line=error.lineno,
                pattern=error.text.strip() if error.text else None,
                details={
                    "filename": filename,
                    "offset": error.offset or 0,
                },
            )
            raise ExportDiagnosticError(diagnostic) from error

    def validate_python_file(self, path: str) -> None:
        file_path = Path(path)
        code = file_path.read_text(encoding="utf-8")
        self.validate_python_syntax(code, filename=str(file_path))
