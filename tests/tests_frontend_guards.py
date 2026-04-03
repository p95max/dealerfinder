from pathlib import Path

from django.conf import settings


class FrontendGuardsTests:
    def test_open_dealer_modal_does_not_use_innerhtml(self):
        search_js_path = Path(settings.BASE_DIR) / "static" / "js" / "search.js"
        content = search_js_path.read_text(encoding="utf-8")

        assert "function openDealerModal" in content

        start = content.index("function openDealerModal")
        end = content.find("document.addEventListener", start)
        function_block = content[start:end] if end != -1 else content[start:]

        assert ".innerHTML" not in function_block
        assert "replaceChildren()" in function_block
        assert "appendInfoRow(" in function_block