"""Web doc fetcher tool for expert council agents."""
import urllib.request
import urllib.error
from agency_swarm.tools import BaseTool
from pydantic import Field


class FetchDocsTool(BaseTool):
    """Fetch and extract text content from a documentation URL."""
    url: str = Field(..., description="URL to fetch documentation from")

    def run(self) -> str:
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; GovernanceBot/1.0)"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Strip HTML tags simply
            import re
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            # Return first 8000 chars to stay within context
            return text[:8000] if len(text) > 8000 else text
        except urllib.error.URLError as e:
            return f"[FetchError] Could not reach {self.url}: {e}"
        except Exception as e:
            return f"[Error] {e}"


class ReadKnowledgeBaseTool(BaseTool):
    """Read the local knowledge base file for a platform."""
    platform: str = Field(
        ...,
        description="Platform name: 'paperclip', 'crewai', or 'openswarm'"
    )

    def run(self) -> str:
        import os
        # Resolve from this file's location: tools/ → council/ → governance/ → Desktop/
        desktop = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        kb_dir = os.path.join(desktop, "ultimate-agent-framework", "council", "knowledge-base")
        fname = f"{self.platform}-patterns.md"
        path = os.path.join(kb_dir, fname)
        try:
            with open(path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return f"[Error] Knowledge base not found: {path}"
