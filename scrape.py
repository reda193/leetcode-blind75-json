import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def scrape_leetcode_questions(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "text-title-large"))
        )
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-track-load='description_content']"))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        title_element = soup.find('div', class_='text-title-large')
        full_title = title_element.find('a').get_text().strip() if title_element else "Title not found"

        # Extract problem number from title
        problem_number = ""
        title = full_title
        if '. ' in full_title:
            problem_number, title = full_title.split('. ', 1)

        difficulty_element = (
                soup.find('div', class_='text-difficulty-easy') or
                soup.find('div', class_='text-difficulty-medium') or
                soup.find('div', class_='text-difficulty-hard')
        )
        difficulty = difficulty_element.get_text().strip() if difficulty_element else "Difficulty not found"

        description_element = soup.find('div', {'data-track-load': 'description_content'})
        description = description_element.get_text().strip() if description_element else "Description not found"

        print(f"Problem Number: {problem_number}")
        print(f"Title: {title}")
        print(f"Difficulty: {difficulty}")
        print(f"Description: {description}")

        return {
            "problem_number": problem_number,
            "title": title,
            "difficulty": difficulty,
            "description": description
        }

    except Exception as e:
        print(f"Error: {e}")
        print("Detailed error information:")
        import traceback
        traceback.print_exc()

    finally:
        if 'driver' in locals():
            driver.quit()


def scrape_leetcode_urls(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-infobars')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "discuss-markdown-container"))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find the markdown container that contains the problem list
        markdown_container = soup.find('div', class_='discuss-markdown-container')
        if not markdown_container:
            return []

        links = markdown_container.find_all('a')

        modified_urls = []
        url_count = 0

        for link in links:
            href = link.get('href')
            if href and 'leetcode.com/problems/' in href:
                modified_url = href + 'description/'
                modified_urls.append(modified_url)
                url_count += 1
                print(f"Found URL {url_count}/75: {modified_url}")

                # Safety check - should only be 75 problems
                if url_count >= 75:
                    break

        print(f"\nTotal URLs found: {len(modified_urls)}")
        return modified_urls

    except Exception as e:
        print(f"Error: {e}")
        print("Detailed error information:")
        import traceback
        traceback.print_exc()
        return []

    finally:
        if 'driver' in locals():
            driver.quit()

def save_json(problems_dict, filename='leetcode_problems.json'):
    """Separate function to handle JSON saving"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(problems_dict, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving JSON: {e}")
        return False


def main():
    url2 = "https://leetcode.com/discuss/general-discussion/460599/blind-75-leetcode-questions"

    # Add delay between scraping operations
    time.sleep(2)

    try:
        problem_urls = scrape_leetcode_urls(url2)
        if not problem_urls:
            print("No URLs found. Exiting...")
            return

        print(f"Found {len(problem_urls)} URLs to process")

        all_problems = {}
        start_time = time.time()

        def process_url(url):
            time.sleep(1)  # Add small delay between requests
            try:
                result = scrape_leetcode_questions(url)
                if result and result.get('problem_number'):
                    return result
            except Exception as e:
                print(f"Error processing {url}: {e}")
                return None

        # Reduce number of workers to avoid overwhelming the server
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_url = {executor.submit(process_url, url): url for url in problem_urls}

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        problem_number = result['problem_number']
                        all_problems[problem_number] = {
                            "title": result['title'],
                            "difficulty": result['difficulty'],
                            "description": result['description']
                        }
                        print(f"Completed problem {problem_number}: {result['title']}")

                        # Save after each successful scrape
                        save_json(all_problems)

                except Exception as e:
                    print(f"Error processing result from {url}: {e}")

        end_time = time.time()
        duration = end_time - start_time
        print(f"\nCompleted in {duration:.2f} seconds")
        print(f"Total problems scraped: {len(all_problems)}")

        # Final save attempt
        if all_problems:
            save_json(all_problems)

    except Exception as e:
        print(f"Main execution error: {e}")
        if 'all_problems' in locals() and all_problems:
            print("Attempting to save partial results...")
            save_json(all_problems)


if __name__ == "__main__":
    main()