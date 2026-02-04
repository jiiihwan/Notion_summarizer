import os
import requests
import logging

class NotionConnector:
    def __init__(self):
        self.token = os.environ["NOTION_TOKEN"]
        
        # Clean up Source ID (Handle cases like 'Page-Title-32charID')
        raw_id = os.environ["NOTION_DATABASE_ID"]
        # If ID is part of a URL or has name prefix with hyphen, usually the ID is the last 32 chars
        # Notion IDs are 32 hex chars (sometimes with dashes).
        # Heuristic: split by '-' and check if the last part is 32 chars hex, usually it works.
        # But easier: if len > 32 and it looks like name-id, just take last 32 chars.
        if len(raw_id) > 32 and "-" in raw_id and not raw_id.count("-") == 4: # 4 dashes is standard UUID format
             # Assume format: Name-of-Page-32charID
             self.source_id = raw_id[-32:]
             logging.getLogger(__name__).info(f"Auto-cleaned Source ID: {raw_id} -> {self.source_id}")
        else:
             self.source_id = raw_id
             
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.base_url = "https://api.notion.com/v1"
        self.logger = logging.getLogger(__name__)
        
        # Detect source type and properties
        self.source_type = "unknown"
        self.title_property_name = "title" # Default for pages
        self._detect_source_type()

    def _detect_source_type(self):
        """
        Determines if the provided ID is a Database or a Page.
        """
        # 1. Try Database
        url_db = f"{self.base_url}/databases/{self.source_id}"
        resp_db = requests.get(url_db, headers=self.headers)
        if resp_db.status_code == 200:
            self.source_type = "database"
            self.logger.info("Source detected as: DATABASE")
            return
            
        # 2. Try Page
        url_page = f"{self.base_url}/pages/{self.source_id}"
        resp_page = requests.get(url_page, headers=self.headers)
        if resp_page.status_code == 200:
            self.source_type = "page"
            self.logger.info("Source detected as: PAGE (Nested Pages Mode)")
            return
            
        self.logger.error(f"Could not identify source ID '{self.source_id}'. Check permissions or ID validity.")

    def fetch_unsummarized_pages(self):
        if self.source_type == "database":
            return self._fetch_from_database()
        elif self.source_type == "page":
            return self._fetch_from_page()
        return []

    def _fetch_from_database(self):
        """
        Fetches pages from the database using requests.
        Filters out pages that are already summaries (start with '[AI Summary]').
        Also detects the real name of the 'title' property.
        """
        url = f"{self.base_url}/databases/{self.source_id}/query"
        try:
            response = requests.post(url, headers=self.headers, json={})
            if response.status_code != 200:
                self.logger.error(f"Error fetching database: {response.text}")
                return []
            
            results = response.json().get("results", [])
            
            # Detect properties schema from the first result
            if results:
                first_props = results[0].get("properties", {})
                for name, prop in first_props.items():
                    if prop["type"] == "title":
                        self.title_property_name = name
                        self.logger.info(f"Detected Title Property: '{name}'")
                    elif prop["type"] == "date":
                        self.date_property_name = name
                        self.logger.info(f"Detected Date Property: '{name}'")
                    elif prop["type"] == "multi_select":
                        self.tag_property_name = name
                        self.logger.info(f"Detected Tag (Multi-Select) Property: '{name}'")
            
            filtered_results = []
            for page in results:
                # Check title
                title = "Untitled"
                props = page.get("properties", {})
                
                # Fetch title value irrespective of property name
                for prop_val in props.values():
                    if prop_val["type"] == "title":
                        title_list = prop_val.get("title", [])
                        if title_list:
                            title = title_list[0].get("plain_text", "")
                        break
                
                if not title.startswith("[AI Summary]"):
                    filtered_results.append(page)
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Error fetching database: {e}")
            return []

    def _fetch_from_page(self):
        """
        Fetches the parent page content AND recursively searches for 
        child pages and child databases (even inside callouts/toggles).
        """
        filtered_results = []
        
        try:
            # 1. Fetch Parent Page itself
            parent_url = f"{self.base_url}/pages/{self.source_id}"
            parent_resp = requests.get(parent_url, headers=self.headers)
            if parent_resp.status_code == 200:
                parent_data = parent_resp.json()
                parent_title = "Parent Page"
                props = parent_data.get("properties", {})
                for prop_val in props.values():
                   if prop_val["type"] == "title":
                       t_list = prop_val.get("title", [])
                       if t_list:
                           parent_title = t_list[0].get("plain_text", "Parent Page")
                       break
                
                if not parent_title.startswith("[AI Summary]"):
                    self.logger.info(f"Adding Parent Page: {parent_title}")
                    filtered_results.append(parent_data)

            # 2. Recursive Search for Children
            self.logger.info("Scanning for nested pages and databases...")
            nested_items = self._collect_nested_content(self.source_id)
            filtered_results.extend(nested_items)
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Error fetching page content: {e}")
            return []

    def _collect_nested_content(self, block_id, depth=0):
        """
        Recursively fetches blocks to find child_page and child_database.
        Limit depth to prevent infinite loops or excessive interaction.
        """
        found_items = []
        if depth > 3: # Optimized depth limit to 3
            return found_items

        url = f"{self.base_url}/blocks/{block_id}/children"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return found_items
            
            results = response.json().get("results", [])
            
            for block in results:
                b_type = block["type"]
                
                # Case A: Child Page
                if b_type == "child_page":
                    title = block["child_page"].get("title", "Untitled")
                    if not title.startswith("[AI Summary]"):
                        # Mock structure for consistency
                        mock_page = block.copy()
                        mock_page['properties'] = {
                            "title": { "type": "title", "title": [{"plain_text": title}] }
                        }
                        found_items.append(mock_page)
                        self.logger.info(f"Found Child Page: {title}")

                # Case B: Child Database
                elif b_type == "child_database":
                    db_title = block["child_database"].get("title", "Untitled Database")
                    self.logger.info(f"Found Inline Database: {db_title}")
                    # Query this database to get its pages
                    db_pages = self._fetch_pages_from_inline_db(block["id"])
                    found_items.extend(db_pages)

                # Case C: Container Block (Callout, Toggle, Column, etc.)
                # If it has children, recurse!
                elif block.get("has_children"):
                    nested = self._collect_nested_content(block["id"], depth + 1)
                    found_items.extend(nested)
                    
        except Exception as e:
            self.logger.error(f"Error traversing block {block_id}: {e}")
            
        return found_items

    def _fetch_pages_from_inline_db(self, database_id):
        """
        Queries an inline database found inside a page.
        """
        url = f"{self.base_url}/databases/{database_id}/query"
        try:
            response = requests.post(url, headers=self.headers, json={})
            if response.status_code != 200:
                return []
            
            results = response.json().get("results", [])
            valid_pages = []
            for page in results:
                title = "Untitled"
                props = page.get("properties", {})
                for prop_val in props.values():
                    if prop_val["type"] == "title":
                        t_list = prop_val.get("title", [])
                        if t_list:
                            title = t_list[0].get("plain_text", "")
                        break
                
                if not title.startswith("[AI Summary]"):
                    valid_pages.append(page)
            
            self.logger.info(f"  -> Extracted {len(valid_pages)} pages from inline DB.")
            return valid_pages
        except Exception as e:
            self.logger.error(f"Error querying inline DB {database_id}: {e}")
            return []

    def get_page_text_content(self, page_id):
        """
        Recursively retrieves text content from a page's blocks, including nested blocks
        (Callouts, Toggles, Columns, etc.).
        """
        return self._get_block_text_recursive(page_id)

    def _get_block_text_recursive(self, block_id, depth=0):
        """
        DFS to traverse block children and extract text.
        """
        all_text = []
        if depth > 3: # Limit depth to optimize speed
            return ""

        url = f"{self.base_url}/blocks/{block_id}/children"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                 self.logger.error(f"Error getting blocks: {response.text}")
                 return ""
                 
            blocks = response.json().get("results", [])
            for block in blocks:
                b_type = block.get("type")
                content = ""
                
                # Extract text from supported block types
                # Added 'callout', 'toggle' to checking list just in case they have direct text
                text_types = [
                    "paragraph", "heading_1", "heading_2", "heading_3", 
                    "bulleted_list_item", "numbered_list_item", "to_do", 
                    "quote", "callout", "toggle"
                ]
                
                if b_type in text_types:
                     # Most blocks use "rich_text"
                     # Callout also uses "rich_text" inside its object
                     obj = block.get(b_type, {})
                     rich_text = obj.get("rich_text", [])
                     if rich_text:
                         text_str = "".join([t.get("plain_text", "") for t in rich_text])
                         if text_str:
                             # Add some formatting context
                             if b_type == "heading_1": content = f"# {text_str}"
                             elif b_type == "heading_2": content = f"## {text_str}"
                             elif b_type == "heading_3": content = f"### {text_str}"
                             elif b_type == "bulleted_list_item": content = f"- {text_str}"
                             elif b_type == "numbered_list_item": content = f"1. {text_str}"
                             elif b_type == "to_do": 
                                 checked = "x" if obj.get("checked") else " "
                                 content = f"- [{checked}] {text_str}"
                             elif b_type == "quote": content = f"> {text_str}"
                             elif b_type == "callout": content = f"> 💡 {text_str}" # Distinguish callout
                             else: content = text_str
                
                if content:
                    all_text.append(content)
                
                # RECURSION: Check for children (Callouts, Toggles, Columns, etc.)
                if block.get("has_children"):
                    nested_text = self._get_block_text_recursive(block["id"], depth + 1)
                    if nested_text:
                        # Indent nested text for better structure context (optional but good)
                        all_text.append(nested_text)

            return "\n".join(all_text)
            
        except Exception as e:
            self.logger.error(f"Error reading page content {block_id}: {e}")
            return ""

    def create_summary_page(self, original_page_id, original_title, summary_content):
        """
        Creates a new PAGE (row) in the DATABASE with the summary.
        Handles long summaries by splitting into multiple blocks.
        """
        url = f"{self.base_url}/pages"
        
        # Use the detected title property name
        prop_name = self.title_property_name
        
    def create_summary_page(self, original_page_id, original_title, summary_content):
        """
        Creates a new PAGE (row) in the DATABASE with the summary.
        Parses Markdown to create appropriate Notion blocks.
        Sets '날짜' to today and '유형' to '요약'.
        """
        from datetime import datetime
        url = f"{self.base_url}/pages"
        
        # Use the detected title property name
        prop_name = self.title_property_name
        
        # Parse Summary Content into Notion Blocks
        summary_blocks = self._parse_markdown_to_blocks(summary_content)
        
        # Prepare Children Blocks (Only summary content)
        children_blocks = summary_blocks
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Prepare Payload
        properties_payload = {}
        
        # 1. DATABASE MODE
        if self.source_type == "database":
            properties_payload[prop_name] = { 
                "title": [
                    {
                        "text": {"content": f"[AI Summary] {original_title}"}
                    }
                ]
            }
            # Add Date/Tags if detected
            if hasattr(self, 'date_property_name'):
                properties_payload[self.date_property_name] = {
                    "date": { "start": today }
                }
            if hasattr(self, 'tag_property_name'):
                properties_payload[self.tag_property_name] = {
                    "multi_select": [ {"name": "요약"} ]
                }
            
            payload = {
                "parent": {"database_id": self.source_id},
                "properties": properties_payload,
                "children": children_blocks
            }
            
        # 2. PAGE MODE
        else:
            # For child pages, parent is 'page_id' and we only send 'title' property (key is literal 'title')
            payload = {
                "parent": {"page_id": self.source_id},
                "properties": {
                    "title": [ # In page creation, property name is always 'title'
                        {
                            "text": {"content": f"[AI Summary] {original_title}"}
                        }
                    ]
                },
                "children": children_blocks
            }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code != 200:
                self.logger.error(f"Error creating summary page: {response.text}")
                # Fallback: Try without headers if they fail (e.g. wrong property names)
                if "validation_error" in response.text:
                    self.logger.warning("Retrying creation without '날짜'/'유형' properties (might be incorrect names)...")
                    del properties_payload["날짜"]
                    del properties_payload["유형"]
                    payload["properties"] = properties_payload
                    response = requests.post(url, headers=self.headers, json=payload)
                    if response.status_code == 200:
                        return response.json()
                        
                return None
            return response.json()
        except Exception as e:
            self.logger.error(f"Error creating summary page: {e}")
            return None

    def _parse_markdown_to_blocks(self, text):
        """
        Simple Markdown parser to convert text lines into Notion blocks.
        Supports: Headers (#), Bullet Lists (-), Numbered Lists (1.), Quotes (>), and Dividers (---).
        """
        blocks = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Truncate extremely long lines limit to safe guard against 400 bad request
            if len(line) > 2000:
                line = line[:2000]

            block = None
            
            if line == '---' or line == '***' or line == '___':
                block = {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                }
            elif line.startswith('# '):
                block = {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": self._parse_rich_text(line[2:])}
                }
            elif line.startswith('## '):
                block = {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": self._parse_rich_text(line[3:])}
                }
            elif line.startswith('### '):
                block = {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": self._parse_rich_text(line[4:])}
                }
            elif line.startswith('- ') or line.startswith('* '):
                 block = {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": self._parse_rich_text(line[2:])}
                }
            elif len(line) > 2 and line[0].isdigit() and line[1] == '.' and line[2] == ' ': # check "1. "
                 content = line[3:]
                 block = {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {"rich_text": self._parse_rich_text(content)}
                }
            elif line.startswith('> '):
                 block = {
                    "object": "block",
                    "type": "quote",
                    "quote": {"rich_text": self._parse_rich_text(line[2:])}
                }
            else:
                 block = {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": self._parse_rich_text(line)}
                }
            
            if block:
                blocks.append(block)
                
        return blocks

    def _parse_rich_text(self, text):
        """
        Parses text for simple markdown formatting (currently only **bold**).
        Returns a list of Notion rich_text objects.
        """
        rich_text = []
        # Split by ** to identify bold parts
        parts = text.split('**')
        
        for i, part in enumerate(parts):
            if not part:
                continue
                
            # Even index parts are normal text, Odd index parts are bold
            is_bold = (i % 2 == 1)
            
            text_obj = {
                "text": {"content": part},
                "annotations": {"bold": is_bold}
            }
            rich_text.append(text_obj)
            
        if not rich_text:
             # Fallback if empty
             return [{"text": {"content": text}}]
             
        return rich_text
