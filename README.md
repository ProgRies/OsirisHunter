# Project Overview

This script is designed to scrape contact information from German government websites, specifically focusing on identifying points of contact within social media or press teams. The script reads URLs from a CSV file, scrapes relevant subpages, extracts contact details, and updates the CSV with the found information.

## Dependencies

- `csv`
- `requests`
- `BeautifulSoup` from `bs4`
- `dotenv`
- `os`
- `OpenAI` from `openai`
- `urllib.parse`
- `argparse`
- `re`
- `json`

## Setup

1. Ensure that all dependencies are installed. You can install them using pip:

pip install requests beautifulsoup4 python-dotenv openai

2. Create a `.env` file in the project directory and add your OpenAI API key:

OPENAI_API_KEY=your_openai_api_key_here

3. Prepare a CSV file named `landkreise.csv` with the following columns:
- Name
- Population
- Website
- Contact Name
- Email
- Phone

## How to Use

1. **Run the Script:**
Execute the script using Python:

python script_name.py [--debug]

- Use the `--debug` flag for additional print statements during execution.

2. **Process Flow:**
- The script reads the URLs from the CSV file.
- It scrapes the main page of each URL to extract all hyperlinks (hrefs).
- It identifies relevant subpages likely to contain contact information.
- It scrapes plaintext content from these subpages and evaluates the best contact information.
- The contact information is parsed and updated in the CSV file.

## Main Functions

- **execute_prompt(prompt, debug):** Executes a prompt using the OpenAI API and returns the response.
- **parse_contact_info(contact_info, debug):** Parses and extracts the most relevant contact details from the provided content.
- **update_csv(file_path, url, contact_name, email, phone):** Updates the CSV file with the extracted contact information.
- **read_csv(file_path):** Reads URLs from the CSV file.
- **scrape_hrefs(url):** Scrapes all hyperlinks from a given URL.
- **identify_relevant_subpages(hrefs, base_url, debug):** Identifies the most relevant subpages likely to contain contact information.
- **scrape_plaintext_content(url):** Scrapes and returns plaintext content from a given URL.
- **collect_contact_info(subpages, debug):** Collects and compiles contact information from relevant subpages.
- **evaluate_best_contact_info(contact_info, debug):** Evaluates and selects the best contact information from the collected data.

## Execution Example

To run the script with debug mode enabled, use:

python script_name.py --debug
