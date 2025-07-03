from dotenv import load_dotenv
import csv
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import re  # Import the regex module

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Generic function to execute a prompt using the OpenAI client
def execute_prompt(prompt):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        response = completion.choices[0].message.content.strip()
        return response
    except Exception as e:
        print(f"Error executing prompt: {e}")
        return None

# Function to get potential URLs from the LLM
def get_potential_urls(municipality_name):
    prompt = (
        f"Ich suche die offizielle URL für die Website der deutsche Stadt / Gemeinde / Kommune '{municipality_name}'. "
        "Bitte schlage die URL der offizielle Website vor wenn du dir sicher bist, oder bis zu 3 URLs, die höchstwahrscheinlich die offizielle Website der Stadt sind. "
        "Die URLs sollten eine '.de' Domain haben und im Format einer offiziellen Stadt-Website sein, z.B. 'stadtname.de'. Erkläre deine Antwort nicht, antworte nur mit den URLs."
        "Schreibe die URLs in diesem Format:\n"
        "1. beispiel.de\n"
        "2. beispiel.de\n"
        "3. beispiel.de\n"
    )
    response = execute_prompt(prompt)
    
    # Print the LLM response for debugging
    # print("LLM Response:", response)  # Removed debugging print statement

    if response:
        # Use regex to find valid URLs, ensuring only the URL is captured
        urls = re.findall(r'\b(?:https?://)?(www\.)?([a-zA-Z0-9-]+\.de|[a-zA-Z0-9-]+\.sachsen\.de)\b', response)
        
        # Maintain order and remove duplicates from the end
        unique_domains = []
        seen_domains = set()
        
        # Iterate in reverse to keep the first occurrences
        for url in reversed(urls):
            domain = url[1]  # Get the domain part
            # Normalize by removing 'www.' and check for duplicates
            normalized_domain = domain.replace('www.', '')
            if normalized_domain not in seen_domains:
                seen_domains.add(normalized_domain)
                unique_domains.append(normalized_domain)

        # Reverse the list to restore original order
        unique_domains.reverse()

        # Format the unique domains to include https://
        formatted_urls = [f"https://{domain}" for domain in unique_domains]
        # print("Extracted URLs:", formatted_urls)  # Removed this print statement
        return formatted_urls[:5]  # Return the first 5 valid URLs
    return []

def get_official_website(municipality_name):
    # Get potential URLs from the LLM
    potential_urls = get_potential_urls(municipality_name)
    
    for url in potential_urls:
        if url_exists(url):
            try:
                # Fetch the content of the website with a timeout of 10 seconds
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    # Extract plain text from the HTML content
                    plain_text = BeautifulSoup(response.content, 'html.parser').get_text()

                    # Limit the plain text to the first 1500 characters
                    plain_text = plain_text[:3000]  # Truncate to 1500 characters

                    # Ask the LLM if the content looks like the official website
                    prompt = (
                        f"Ist dies die offizielle Website für die Stadt '{municipality_name}'?\n"
                        "Wenn du denkst, es handelt sich hier höchstwahrscheinlich um die offizielle Website, antworte mit [JA]."
                        f"Hier ist ein Teil des Textes, gescrapped von der Startseite: '{plain_text}'.\n"
                    )
                    llm_response = execute_prompt(prompt)

                    if llm_response and "[JA]" in llm_response:  # Check if the LLM confirms
                        return url  # Return the confirmed official URL
            except (requests.Timeout, requests.ConnectionError) as e:
                print(f"Timeout occurred while checking {url}.")  # Optional: log the timeout
                return "Website not found"  # Return "Website not found" on timeout
    return "Website not found"

def url_exists(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

# Read from the CSV file and look up each municipality
with open('Gemeinden Deutschland .csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    rows = list(reader)  # Read all rows into memory for writing later

# Process each row one by one
for index, row in enumerate(rows):
    # Check if the 'Website' column is already filled
    if row['Website'] == "Website not found":  # Check if the previous attempt failed
        print(f"Retrying for {row['Gemeinde']} as the website was not found.")
        topic = row['Gemeinde']
        official_website = get_official_website(topic)  # Try again
        if official_website == "Website not found":  # Check if still not found
            row['Website'] = "No Website"  # Update to "No Website"
        else:
            row['Website'] = official_website  # Update the row with the new result
    elif row['Website']:  # Skip rows where a URL is already present
        print(f"Skipping {row['Gemeinde']} as it already has a URL.")
        continue
    else:
        topic = row['Gemeinde']
        official_website = get_official_website(topic)
        row['Website'] = official_website  # Add the official website to the row

    print(f"Official Website for {topic}: {row['Website']}")
    print(f"------------------------------------------------")

    # Write the updated row back to the CSV file immediately
    with open('Gemeinden Deutschland .csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = reader.fieldnames  # Use the original fieldnames
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()  # Write the header
        # Write all rows up to the current index
        writer.writerows(rows[:index + 1])  # Write rows up to the current one
        # Write the remaining rows without changes
        writer.writerows(rows[index + 1:])  # Write the rest of the rows

# Final write to ensure all rows are saved
with open('Gemeinden Deutschland .csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = reader.fieldnames  # Use the original fieldnames
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()  # Write the header
    writer.writerows(rows)  # Write the updated rows
