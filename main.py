import logging
import sys
import time

from dotenv import load_dotenv
from notion_connector import NotionConnector
from summarizer import GeminiSummarizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def print_banner():
    """Prints a cool ASCII art banner."""
    print("="*45)
    print(r"""
  _   _       _   _                _    ___ 
 | \ | | ___ | |_(_) ___  _ __    / \  |_ _|
 |  \| |/ _ \| __| |/ _ \| '_ \  / _ \  | | 
 | |\  | (_) | |_| | (_) | | | |/ ___ \ | | 
 |_| \_|\___/ \__|_|\___/|_| |_/_/   \_\___|
                                           
        >>> Notion AI Assistant <<<
    """)
    print("="*45 + "\n")

def main():
    load_dotenv()
    
    print_banner()

    # 1. Get User Input
    user_instruction = input("Q. 이 페이지/데이터베이스를 어떻게 요약/분석 해드릴까요?\n   (예: '회고록 써줘', '아이디어만 뽑아서 정리해줘')\n>> ")
    
    if not user_instruction.strip():
        print("입력이 없어 종료합니다.")
        return

    report_title = input("\nQ. 생성될 페이지의 제목을 무엇으로 할까요?\n   (엔터치면 'AI Report'로 저장)\n>> ")
    if not report_title.strip():
        report_title = "AI Report"

    logger.info("Starting process...")
    
    try:
        # Initialize connectors
        notion = NotionConnector()
        summarizer = GeminiSummarizer()
        
        # 2. Fetch Data (All pages, excluding existing summaries)
        logger.info("Fetching pages from Notion...")
        pages = notion.fetch_unsummarized_pages()
        logger.info(f"Found {len(pages)} pages in the database.")

        if not pages:
            logger.info("No pages found to process.")
            return

        # 3. Aggregate Text
        logger.info("Extracting text from pages...")
        aggregated_text = ""
        
        for i, page in enumerate(pages):
            # Rate limiting check (not strictly needed for reading if sequential, but good practice)
            # Fetching content
            page_id = page['id']
            
            # Helper to get title for logging
            title = "Untitled"
            props = page.get("properties", {})
            for prop_val in props.values():
                if prop_val["type"] == "title":
                    title_list = prop_val.get("title", [])
                    if title_list:
                        title = title_list[0].get("plain_text", "")
                    break
            
            # Extract useful properties (Status, Tags, Date, URL, etc.)
            props_text = ""
            for prop_name, prop_val in props.items():
                p_type = prop_val["type"]
                p_content = ""
                
                if p_type == "select":
                    val = prop_val.get("select")
                    if val: p_content = val.get("name", "")
                elif p_type == "multi_select":
                    vals = prop_val.get("multi_select", [])
                    p_content = ", ".join([v.get("name", "") for v in vals])
                elif p_type == "status":
                    val = prop_val.get("status")
                    if val: p_content = val.get("name", "")
                elif p_type == "date":
                    val = prop_val.get("date")
                    if val: 
                        start = val.get("start", "")
                        end = val.get("end", "")
                        p_content = f"{start} ~ {end}" if end else start
                elif p_type == "url":
                    p_content = prop_val.get("url", "")
                elif p_type == "email":
                    p_content = prop_val.get("email", "")
                elif p_type == "checkbox":
                    p_content = "Yes" if prop_val.get("checkbox") else "No"
                
                if p_content:
                    props_text += f"- {prop_name}: {p_content}\n"
            
            logger.info(f"[{i+1}/{len(pages)}] Reading: {title}")
            
            page_content = notion.get_page_text_content(page_id)
            
            # Combine Title + Properties + Content
            aggregated_text += f"\n\n==================================================\n"
            aggregated_text += f"PAGE TITLE: {title}\n"
            aggregated_text += f"--------------------------------------------------\n"
            aggregated_text += f"[Page Properties]\n{props_text}\n"
            aggregated_text += f"--------------------------------------------------\n"
            aggregated_text += f"[Page Content]\n{page_content}\n"
            aggregated_text += f"==================================================\n"

        logger.info(f"Total aggregated text length: {len(aggregated_text)} characters.")
        
        if len(aggregated_text) < 10:
            logger.warning("Text content is too short to summarize.")
            return

        # 4. Summarize (One-shot)
        logger.info("Sending data to Gemini for analysis...")
        summary = summarizer.summarize(aggregated_text, user_instruction=user_instruction)
        
        if not summary or summary.startswith("Failed to generate"):
            logger.error("Failed to generate summary.")
            return

        print("\n" + "-"*30)
        print("Generated Summary Preview (First 200 chars):")
        print(summary[:200])
        print("-"*30 + "\n")
        
        # 5. Save Report
        logger.info(f"Saving report to Notion as '{report_title}'...")
        # Since we aggregate, we don't have a single 'original_page_id', using the first one or None logic?
        # The connector expects an original_page_id for the callout. 
        # Let's modify the connector call or just pass the first one for reference, 
        # OR better, pass None and handle it in connector (need to check connector code).
        # We will point to the database itself conceptually.
        
        # Creating a new page at the database level (as a row)
        new_page = notion.create_summary_page("Aggregate", report_title, summary)
        
        if new_page:
            logger.info("Successfully created report page in Notion! 🎉")
        else:
            logger.error("Failed to create report page.")
                
    except Exception as e:
        logger.error(f"Critical error: {e}")

if __name__ == "__main__":
    main()
