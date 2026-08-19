"""Domain service for parsing .ragignore patterns and enforcing security sanitization."""

import fnmatch
from pathlib import Path

COMPULSORY_BLACKLIST_PATTERNS = [
    "*.env*",
    "*.pem",
    "*.key",
    "*secret*",
    "*credentials*",
    "*id_rsa*",
    "node_modules/*",
    ".venv*/*",
    "__pycache__/*",
    ".git/*",
    "*.pyc",
]


class RagIgnoreFilter:
    """Sanitizes document file paths against .ragignore rules and mandatory security blacklists."""

    def __init__(self, root_dir: str | Path, custom_patterns: list[str] | None = None) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.patterns: list[str] = list(COMPULSORY_BLACKLIST_PATTERNS)

        if custom_patterns:
            self.patterns.extend(custom_patterns)

        ragignore_file = self.root_dir / ".ragignore"
        if ragignore_file.is_file():
            try:
                lines = ragignore_file.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        self.patterns.append(stripped)
            except Exception:
                pass

    def is_ignored(self, file_path: str | Path) -> bool:
        """Return True if relative or absolute path matches any ignore pattern."""
        path_obj = Path(file_path)
        try:
            rel_path = str(path_obj.relative_to(self.root_dir))
        except ValueError:
            rel_path = str(path_obj)

        norm_path = rel_path.replace("\\", "/")
        base_name = path_obj.name.lower()

        # Check exact and glob pattern matches
        for pat in self.patterns:
            pat_lower = pat.lower()
            if fnmatch.fnmatch(base_name, pat_lower) or fnmatch.fnmatch(norm_path, pat_lower):
                return True
            if pat_lower.endswith("/") and fnmatch.fnmatch(norm_path + "/", pat_lower):
                return True

        return False
