import csv
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from openai import OpenAI
from urllib.parse import urljoin
import argparse
import re
import json

# Load environment variables from the .env file
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Function to execute the prompt using the correct OpenAI client method
def execute_prompt(prompt, debug):
    try:
        if debug:
            print("\n--- Executing LLM Prompt ---")
            print(f"Prompt:\n{prompt}")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in navigating German government websites."},
                {"role": "user", "content": prompt}
            ]
        )
        response = completion.choices[0].message.content.strip()
        # print(f"\nResponse:\n{response}")
        if debug:
            print("--- LLM Prompt Execution Completed ---\n")
        return response
    except Exception as e:
        print(f"Failed to execute GPT prompt: {e}")
        return None

# Function to parse contact information from the LLM response
def parse_contact_info(contact_info, debug):
    # Assume contact_info is always a string
    combined_content = contact_info

    prompt = (
        "Based on the provided content, and based on what URL that content was found,"
        " extract the most relevant point of contact details for a person likely to be from the "
        "social media or press team. Provide the details in the structured format below."
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant specialized in extracting contact information from website content."},
        {"role": "user", "content": combined_content},
        {"role": "user", "content": prompt},
    ]

    function_call = {
        "name": "extract_contact_info",
        "description": "Extracts the best contact information from the provided text.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The full name of the contact person."},
                "email": {"type": "string", "description": "The email address of the contact person."},
                "phone": {"type": "string", "description": "The phone number of the contact person."},
            },
            "required": ["name", "email", "phone"],
        },
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            functions=[function_call],
            function_call="auto",
        )

        if response.choices[0].finish_reason == "function_call":
            function_call_info = response.choices[0].message.function_call

            contact_details = json.loads(function_call_info.arguments)
            contact_name = contact_details.get("name", "N/A")
            email = contact_details.get("email", "N/A")
            phone = contact_details.get("phone", "N/A")

            return contact_name, email, phone
        else:
            print("The AI did not produce a function call result.")
            return 'N/A', 'N/A', 'N/A'

    except Exception as e:
        print(f"Error in extracting contact information: {e}")
        return 'N/A', 'N/A', 'N/A'

# Function to update the CSV file with extracted contact information
def update_csv(file_path, url, contact_name, email, phone):
    try:
        # Read the CSV file and store rows in memory
        with open(file_path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            rows = list(csv_reader)  # Read all rows into memory for processing

        # Update the rows in memory
        for row in rows:
            if row['Website'] == url:
                row['Contact Name'] = contact_name
                row['Email'] = email
                row['Phone'] = phone

        # Write the updated rows back to the CSV file
        with open(file_path, mode='w', encoding='utf-8', newline='') as file:
            fieldnames = ['Gemeinde', 'Einwohner', 'Website', 'Contact Name', 'Email', 'Phone', 'Email Status', 'Notes']  # Updated field names
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
            csv_writer.writeheader()  # Write the header back to the file
            csv_writer.writerows(rows)  # Write all updated rows back to the file

        print(f"Updated CSV file successfully for {url}.")
    except Exception as e:
        print(f"Failed to update CSV file: {e}")

# Function to read CSV file and extract URLs
def read_csv(file_path):
    urls = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                contact_name = row['Contact Name']
                email = row['Email']
                phone = row['Phone']

                # Check if the row is empty or contains only "N/A" values
                if (not contact_name or contact_name == 'N/A') and (not email or email == 'N/A') and (not phone or phone == 'N/A'):
                    urls.append(row['Website'])

            print(f"Successfully read {len(urls)} URLs from the CSV file.")
    except Exception as e:
        print(f"Failed to read CSV file: {e}")
    return urls

# Function to scrape a website and extract all hrefs
def scrape_hrefs(url):
    try:
        print(f"Scraping hrefs from: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, timeout=5)  # Added timeout parameter
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            hrefs = [a['href'] for a in soup.find_all('a', href=True)]
            # print(f"Found {len(hrefs)} hrefs on {url}")
            return hrefs
        else:
            print(f"Failed to retrieve {url}: Status code {response.status_code}")
            return []
    except Exception as e:
        print(f"Error scraping hrefs from {url}: {e}")
        return []


# Function to identify relevant subpages based on hrefs
def identify_relevant_subpages(hrefs, base_url, debug):
    print("Identifying relevant subpages...")

    resolved_hrefs = [urljoin(base_url, href) for href in hrefs]

    hrefs_prompt = "\n".join(resolved_hrefs)
    prompt = f"Here is a list of hrefs from a German government website. Return the three links that are most likely to include contact information of the press and/or social media teams. Return nothing else.\n\n{hrefs_prompt}"
    response = execute_prompt(prompt, debug)

    if response:
        try:
            selected_hrefs = re.findall(r'https?://\S+', response)
            selected_hrefs = [href for href in selected_hrefs if href in resolved_hrefs]

            # print("Suggested relevant subpages:")
            # for link in selected_hrefs:
                # print(f"- {link}")
            return selected_hrefs
        except Exception as e:
            print(f"Error parsing response for href selection: {e}")
            return []
    return []

# Function to scrape a website and extract all plaintext
def scrape_plaintext_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers, timeout=5)  # Added timeout parameter
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text_content = soup.get_text(separator='\n').strip()
            cleaned_text = "\n".join(line.strip() for line in text_content.splitlines() if line.strip())
            return cleaned_text
        else:
            print(f"Failed to retrieve {url}: Status code {response.status_code}")
            return ""
    except Exception as e:
        print(f"Error scraping content from {url}: {e}")
        return ""


# Function to collect contact information from relevant subpages
def collect_contact_info(subpages, debug):
    contact_info = []
    for subpage in subpages:
        content = scrape_plaintext_content(subpage)
        if content:
            contact_info.append((subpage, content))
        else:
            print(f"No content found on subpage {subpage}. Moving to the next subpage.")
    return contact_info

# Function to evaluate and select the best contact information
def evaluate_best_contact_info(contact_info, debug):
    combined_content = "\n\n".join([f"URL: {url}\n{content}" for url, content in contact_info])
    prompt = (
        "Here is the combined contact information extracted from several subpages of a German government website. "
        "Based on the content and the URLs provided, determine which contact details are most likely from someone in "
        "the social media or press team. Prioritize any named contacts with direct emails or phone numbers over generic ones. "
        "Respond with the best single point of contact in the format: Name:, Email:, Phone, nothing else.\n\n"
        f"{combined_content}"
    )
    return execute_prompt(prompt, debug)

# Main process
def main():
    parser = argparse.ArgumentParser(description="Process some URLs.")
    parser.add_argument('--debug', action='store_true', help="Enable debug mode to print additional details.")
    args = parser.parse_args()

    file_path = 'with_urls_gemeinden_deutschland.csv'

    print("Starting the process...")
    urls = read_csv(file_path)

    for index, url in enumerate(urls):
        print(f"\nProcessing website: {url}")

        # Check if the URL contains "No Website"
        if "No Website" in url:
            print(f"Skipping {url} as it contains 'No Website'. Setting contact info to 'N/A'.")
            update_csv(file_path, url, 'N/A', 'N/A', 'N/A')  # Set contact info to 'N/A'
            continue

        hrefs = scrape_hrefs(url)
        if not hrefs:
             #print(f"No hrefs found or an error occurred for {url}. Skipping to the next website.")
            continue

        subpages = identify_relevant_subpages(hrefs, url, args.debug)
        if not subpages:
             #print(f"No relevant subpages identified for {url}. Skipping to the next website.")
            continue

        contact_info = collect_contact_info(subpages, args.debug)
        if not contact_info:
             #print(f"No contact information collected from {url}. Moving to the next website.")
            continue

        best_contact = evaluate_best_contact_info(contact_info, args.debug)
        if best_contact:
            # print(f"\nBest contact information for {url}:\n{best_contact}")

            contact_name, email, phone = parse_contact_info(best_contact, args.debug)
            update_csv(file_path, url, contact_name, email, phone)
        else:
            print(f"No valid contact information found for {url}.")

        print(f"Finished processing website: {url}")

    print("Process completed.")

if __name__ == "__main__":
    main()
