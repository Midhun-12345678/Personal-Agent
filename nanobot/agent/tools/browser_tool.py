"""Browser tool: Navigate websites, fill forms, click buttons, and extract information."""

import json
import re
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool


def _strip_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    # Remove script and style elements
    html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.I)
    html = re.sub(r'<style[\s\S]*?</style>', '', html, flags=re.I)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


class BrowserTool(Tool):
    """Navigate websites, fill forms, click buttons, and extract information from web pages."""

    name = "browser"
    description = "Navigate websites, fill forms, click buttons, and extract information from web pages"
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "fill_form", "click", "extract"],
                "description": "Action to perform"
            },
            "url": {
                "type": "string",
                "description": "URL to navigate to"
            },
            "fields": {
                "type": "object",
                "description": "Form fields to fill (for action='fill_form'). Keys are field labels/names, values are what to fill"
            },
            "selector": {
                "type": "string",
                "description": "CSS selector of element to click (for action='click')"
            },
            "extract_what": {
                "type": "string",
                "description": "Description of what information to extract (for action='extract')"
            }
        },
        "required": ["action", "url"]
    }

    def __init__(self, headless: bool = True, provider=None):
        """Initialize Browser tool.
        
        Args:
            headless: Run browser in headless mode
            provider: LLM provider for extract action (optional)
        """
        self.headless = headless
        self.provider = provider
        self._browser = None
        self._playwright = None

    async def _get_browser(self):
        """Get or create browser instance."""
        if self._browser:
            return self._browser

        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            return self._browser
        except Exception as e:
            logger.error("Browser launch failed: {}", e)
            raise

    async def _close_browser(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def execute(self, action: str, url: str, **kwargs: Any) -> str:
        if not url:
            return json.dumps({"error": "url is required"})

        # Validate URL
        if not url.startswith(("http://", "https://")):
            return json.dumps({"error": "URL must start with http:// or https://"})

        try:
            if action == "navigate":
                return await self._navigate(url, **kwargs)
            elif action == "fill_form":
                return await self._fill_form(url, **kwargs)
            elif action == "click":
                return await self._click(url, **kwargs)
            elif action == "extract":
                return await self._extract(url, **kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ImportError:
            return json.dumps({
                "error": "Playwright not installed",
                "message": "Install with: pip install playwright && playwright install chromium"
            })
        except Exception as e:
            logger.error("Browser {} failed: {}", action, e)
            return json.dumps({"error": str(e)})

    async def _navigate(self, url: str, **kwargs) -> str:
        """Navigate to URL and return page content."""
        browser = await self._get_browser()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            title = await page.title()
            content = await page.content()
            text = _strip_html(content)
            
            # Limit text size
            if len(text) > 15000:
                text = text[:15000] + "... (truncated)"

            return json.dumps({
                "success": True,
                "url": page.url,
                "title": title,
                "content": text
            }, indent=2)
        finally:
            await page.close()

    async def _fill_form(self, url: str, fields: dict = None, **kwargs) -> str:
        """Navigate to URL and fill form fields."""
        if not fields:
            return json.dumps({"error": "fields is required for fill_form action"})

        browser = await self._get_browser()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            filled_fields = []
            for field_key, field_value in fields.items():
                # Try multiple selectors to find the field
                selectors = [
                    f'input[name="{field_key}"]',
                    f'input[placeholder*="{field_key}" i]',
                    f'textarea[name="{field_key}"]',
                    f'textarea[placeholder*="{field_key}" i]',
                    f'input[aria-label*="{field_key}" i]',
                    f'select[name="{field_key}"]',
                ]
                
                # Also try finding by label
                label_selector = f'label:has-text("{field_key}")'
                
                filled = False
                for selector in selectors:
                    try:
                        element = page.locator(selector).first
                        if await element.count() > 0:
                            await element.fill(str(field_value))
                            filled_fields.append(field_key)
                            filled = True
                            break
                    except Exception:
                        continue
                
                # Try label association
                if not filled:
                    try:
                        label = page.locator(label_selector).first
                        if await label.count() > 0:
                            # Get the 'for' attribute or find nearby input
                            for_attr = await label.get_attribute("for")
                            if for_attr:
                                input_el = page.locator(f"#{for_attr}")
                                if await input_el.count() > 0:
                                    await input_el.fill(str(field_value))
                                    filled_fields.append(field_key)
                                    filled = True
                    except Exception:
                        pass

            return json.dumps({
                "success": len(filled_fields) > 0,
                "filled_fields": filled_fields,
                "requested_fields": list(fields.keys()),
                "url": page.url
            }, indent=2)
        finally:
            await page.close()

    async def _click(self, url: str, selector: str = "", **kwargs) -> str:
        """Navigate to URL and click an element."""
        if not selector:
            return json.dumps({"error": "selector is required for click action"})

        browser = await self._get_browser()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Try to click the element
            element = page.locator(selector).first
            if await element.count() == 0:
                return json.dumps({
                    "success": False,
                    "error": f"Element not found: {selector}"
                })
            
            await element.click()
            
            # Wait for any navigation/changes
            await page.wait_for_timeout(1000)
            
            return json.dumps({
                "success": True,
                "result": f"Clicked element matching '{selector}'",
                "current_url": page.url,
                "title": await page.title()
            }, indent=2)
        finally:
            await page.close()

    async def _extract(self, url: str, extract_what: str = "", **kwargs) -> str:
        """Navigate to URL and extract specific information."""
        if not extract_what:
            return json.dumps({"error": "extract_what is required for extract action"})

        browser = await self._get_browser()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            content = await page.content()
            text = _strip_html(content)
            
            # Limit for LLM context
            if len(text) > 10000:
                text = text[:10000]

            # If we have an LLM provider, use it to extract
            if self.provider:
                try:
                    response = await self.provider.chat(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a data extraction assistant. Extract the requested information from the webpage content. Return only the extracted data, no explanations."
                            },
                            {
                                "role": "user",
                                "content": f"Extract the following from this webpage:\n\nRequested: {extract_what}\n\nWebpage content:\n{text}"
                            }
                        ],
                        temperature=0.1,
                        max_tokens=2000
                    )
                    
                    return json.dumps({
                        "success": True,
                        "url": page.url,
                        "data": response.content or "No data extracted"
                    }, indent=2)
                except Exception as e:
                    logger.error("LLM extraction failed: {}", e)
            
            # Fallback: return raw text for manual extraction
            return json.dumps({
                "success": True,
                "url": page.url,
                "note": "No LLM available for smart extraction. Raw content provided.",
                "data": text[:5000]
            }, indent=2)
        finally:
            await page.close()
