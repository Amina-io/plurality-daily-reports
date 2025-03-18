"""
CurateAI - Personalized Knowledge Curation

This script uses the Perplexity API to fetch the latest information about
topics of interest and generate personalized knowledge reports for multiple customers.
"""
import requests
import json
import os
import time
import re
import argparse
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

API_KEY = os.environ.get("PERPLEXITY_API_KEY")
if not API_KEY:
    raise ValueError("Please set the PERPLEXITY_API_KEY environment variable")

# Email configuration
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_SERVER = os.environ.get("EMAIL_SERVER", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))

# Default categories for new users
DEFAULT_CATEGORIES = {
    "research_papers": {
        "description": "Recent academic papers and publications",
        "keyword_groups": {
            "concepts": []
        }
    },
    "industry_news": {
        "description": "Latest news and developments",
        "keyword_groups": {
            "organizations": []
        }
    },
    "events": {
        "description": "Upcoming conferences, events, workshops, talks, and meetups",
        "keyword_groups": {
            "events": []
        }
    },
    "jobs": {
        "description": "Job opportunities, fellowships, grants, and positions",
        "keyword_groups": {
            "jobs": []
        }
    }
}

def load_customer_config(customer_id):
    """
    Load a customer's configuration from their JSON file.
    
    Args:
        customer_id (str): Customer ID
        
    Returns:
        dict: Customer configuration
    """
    config_path = f"customers/{customer_id}/config.json"
    
    if not os.path.exists(config_path):
        # Create new customer directory and default config
        os.makedirs(f"customers/{customer_id}", exist_ok=True)
        os.makedirs(f"customers/{customer_id}/output", exist_ok=True)
        
        default_config = {
            "customer_id": customer_id,
            "email": f"{customer_id}@example.com",
            "name": "New Customer",
            "subscription_tier": "basic",
            "categories": DEFAULT_CATEGORIES,
            "last_run": None
        }
        
        with open(config_path, "w") as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    with open(config_path, "r") as f:
        return json.load(f)

def save_customer_config(config):
    """
    Save a customer's configuration to their JSON file.
    
    Args:
        config (dict): Customer configuration
    """
    customer_id = config["customer_id"]
    config_path = f"customers/{customer_id}/config.json"
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

def get_content_for_group(category_name, group_name, keywords, customer_id):
    """
    Fetches latest content for a specific keyword group using Perplexity API.
    
    Args:
        category_name (str): Name of the category
        group_name (str): Name of the keyword group
        keywords (list): List of keywords to search for
        customer_id (str): Customer ID for tracking
        
    Returns:
        dict: Structured information about the latest content
    """
    url = "https://api.perplexity.ai/chat/completions"
    
    MAX_KEYWORDS_PER_REQUEST = 15
    keyword_chunks = [keywords[i:i + MAX_KEYWORDS_PER_REQUEST] 
                     for i in range(0, len(keywords), MAX_KEYWORDS_PER_REQUEST)]
    
    all_items = []
    
    for chunk in keyword_chunks:
        keywords_str = ", ".join(chunk)
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        category_description = DEFAULT_CATEGORIES[category_name]["description"]
        
        prompt = f"""You are a content curator that sources content for professionals.
Find {category_description} related to the following keywords:
{keywords_str}

IMPORTANT: Only include items from the past 30 days, with a strong preference for items from the past 7 days.
Exclude any content older than 1 month. The current date is {datetime.now().strftime("%Y-%m-%d")}.

Include titles, dates, brief descriptions, links, and sources.
Format your response as a JSON object with the following structure:
{{
  "items": [
    {{
      "title": "Item title",
      "date": "Publication date in YYYY-MM-DD format when possible",
      "description": "Brief description (50 words max)",
      "link": "URL if available",
      "source": "Source name"
    }}
  ]
}}

Only include highly relevant and recent items. Prioritize reputable sources.
If you find fewer than 2 items, expand your search to the past 3 months but clearly mark these as "older content".
Include information from academic journals, podcasts, blogs, LinkedIn, news sites, social media and event websites as appropriate.
"""
        
        data = {
            "model": "sonar-pro", 
            "messages": [
                {
                    "role": "system",
                    "content": "You are a specialized research assistant and content curator, focused on finding and summarizing the latest relevant information."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.2
        }
        
        try:
            print(f"  Making API request for {category_name}/{group_name} (chunk of {len(chunk)} keywords)...")
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            try:
                chunk_results = json.loads(content)
                if "items" in chunk_results and chunk_results["items"]:
                    all_items.extend(chunk_results["items"])
                    print(f"  Found {len(chunk_results['items'])} items for this chunk")
            except json.JSONDecodeError:
                print(f"  Error parsing JSON response for {category_name}/{group_name}. Raw response:")
                print(content[:200] + "..." if len(content) > 200 else content)
                
        except requests.exceptions.RequestException as e:
            print(f"  Error making API request for {category_name}/{group_name}: {str(e)}")
        except (KeyError, IndexError) as e:
            print(f"  Error parsing API response for {category_name}/{group_name}: {str(e)}")
        except Exception as e:
            print(f"  Unexpected error for {category_name}/{group_name}: {str(e)}")
        
        time.sleep(2)
    
    return {"items": all_items}

def get_content_for_category(category_name, category_info, customer_id):
    """
    Fetches latest content for all keyword groups in a category, combining results.
    
    Args:
        category_name (str): Name of the category
        category_info (dict): Dictionary with category description and keyword groups
        customer_id (str): Customer ID for tracking
        
    Returns:
        dict: Combined results from all keyword groups
    """
    print(f"Processing category: {category_name}...")
    all_items = []
    
    for group_name, keywords in category_info["keyword_groups"].items():
        if not keywords:
            continue
            
        group_results = get_content_for_group(category_name, group_name, keywords, customer_id)
        if "items" in group_results:
            all_items.extend(group_results["items"])
    
    # Remove duplicates based on title and link
    unique_items = []
    seen_content = set()
    
    for item in all_items:
        title = item.get("title", "").strip()
        link = item.get("link", "").strip()
        
        # Create a hash of title and link to identify duplicates
        content_hash = hashlib.md5(f"{title}|{link}".encode()).hexdigest()
        
        if content_hash and content_hash not in seen_content:
            seen_content.add(content_hash)
            unique_items.append(item)
    
    print(f"Found {len(unique_items)} unique items for {category_name}")
    return {"items": unique_items}

def get_previous_reports(customer_id, max_reports=10):
    """
    Get a list of previous reports for a customer.
    
    Args:
        customer_id (str): Customer ID
        max_reports (int): Maximum number of previous reports to include
        
    Returns:
        list: List of tuples (date, filename) of previous reports
    """
    reports = []
    output_dir = f"customers/{customer_id}/output"
    
    if not os.path.exists(output_dir):
        return reports
    
    pattern = r"curateai_report_(\d{4}-\d{2}-\d{2})\.html"
    
    for filename in os.listdir(output_dir):
        match = re.match(pattern, filename)
        if match:
            date = match.group(1)
            reports.append((date, filename))
    
    reports.sort(reverse=True)
    
    return reports[:max_reports]

def generate_html_report(results, customer_config):
    """
    Generates an HTML report from the collected results.
    
    Args:
        results (dict): Dictionary mapping categories to their results
        customer_config (dict): Customer configuration
        
    Returns:
        str: HTML content of the report
    """
    customer_id = customer_config["customer_id"]
    customer_name = customer_config["name"]
    subscription_tier = customer_config["subscription_tier"]
    today = datetime.now().strftime("%Y-%m-%d")
    
    previous_reports = get_previous_reports(customer_id)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CurateAI Report for {customer_name} - {today}</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-color: #7050b0;
            --primary-light: #9070d0;
            --primary-dark: #5a3a9a;
            --secondary-color: #aa90f0;
            --text-color: #333;
            --text-light: #7f8c8d;
            --bg-color: #f9f9f9;
            --card-color: white;
            --checked-color: #d4edda;
            --border-radius: 8px;
            --transition-speed: 0.3s;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            display: flex;
            min-height: 100vh;
        }}
        
        .sidebar {{
            width: 250px;
            background-color: var(--primary-light);
            color: white;
            padding: 20px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.1);
            transition: all var(--transition-speed);
        }}
        
        .sidebar h2 {{
            font-family: 'Poppins', sans-serif;
            color: white;
            border-bottom: 1px solid rgba(255, 255, 255, 0.3);
            padding-bottom: 10px;
            margin-top: 0;
            font-weight: 600;
        }}
        
        .sidebar ul {{
            list-style: none;
            padding: 0;
            margin-top: 15px;
        }}
        
        .sidebar li {{
            margin-bottom: 8px;
            border-radius: var(--border-radius);
            overflow: hidden;
            transition: transform var(--transition-speed);
        }}
        
        .sidebar li:hover {{
            transform: translateX(5px);
        }}
        
        .sidebar a {{
            color: #ecf0f1;
            text-decoration: none;
            display: block;
            padding: 8px 10px;
            border-radius: var(--border-radius);
            transition: background-color var(--transition-speed);
        }}
        
        .sidebar a:hover {{
            background-color: var(--primary-dark);
        }}
        
        .sidebar a.active {{
            background-color: var(--primary-dark);
            font-weight: 500;
        }}
        
        .content {{
            flex: 1;
            padding: 30px;
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        h1 {{
            font-family: 'Poppins', sans-serif;
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-light);
            padding-bottom: 10px;
            margin-top: 0;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        
        h2 {{
            font-family: 'Poppins', sans-serif;
            color: var(--primary-color);
            border-left: 4px solid var(--primary-light);
            padding-left: 10px;
            margin-top: 30px;
            margin-bottom: 15px;
            font-weight: 500;
        }}
        
        .item {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            padding: 20px;
            margin-bottom: 20px;
            transition: box-shadow 0.3s ease;
        }}
        
        .item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }}
        
        .item h3 {{
            font-family: 'Poppins', sans-serif;
            color: var(--primary-color);
            margin-top: 0;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        .item p {{
            margin: 5px 0;
        }}
        
        .date {{
            color: var(--text-light);
            font-size: 0.9em;
            margin-bottom: 8px;
        }}
        
        .source {{
            color: var(--text-light);
            font-size: 0.9em;
            text-align: right;
            margin-top: 10px;
        }}
        
        .description {{
            margin: 10px 0;
            line-height: 1.6;
        }}
        
        a {{
            color: var(--primary-color);
            text-decoration: none;
            transition: color var(--transition-speed);
        }}
        
        a:hover {{
            color: var(--primary-dark);
            text-decoration: underline;
        }}
        
        .report-date {{
            text-align: right;
            color: var(--text-light);
            font-size: 0.9em;
            margin-top: 10px;
            margin-bottom: 20px;
        }}
        
        .category-description {{
            font-style: italic;
            color: #555;
            margin-bottom: 20px;
        }}
        
        .no-items {{
            font-style: italic;
            color: var(--text-light);
            padding: 15px;
            background-color: var(--card-color);
            border-radius: var(--border-radius);
            box-shadow: 0 3px 10px rgba(0,0,0,0.05);
        }}
        
        /* Checkbox styling */
        .item-checkbox {{
            display: inline-block;
            margin-right: 10px;
            vertical-align: text-top;
        }}
        
        .item-checkbox input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            cursor: pointer;
        }}
        
        .item.checked {{
            background-color: var(--checked-color);
        }}
        
        .item-header {{
            display: flex;
            align-items: flex-start;
        }}
        
        .item-header h3 {{
            flex: 1;
        }}
        
        .back-button {{
            background-color: var(--primary-dark);
            color: white;
            border: none;
            padding: 8px 12px;
            margin: 10px 0;
            border-radius: var(--border-radius);
            cursor: pointer;
            width: 100%;
            font-weight: 500;
            transition: background-color var(--transition-speed);
        }}
        
        .back-button:hover {{
            background-color: var(--primary-color);
        }}
        
        /* Responsive adjustments */
        @media (max-width: 900px) {{
            body {{
                flex-direction: column;
            }}
            
            .sidebar {{
                width: 100%;
                height: auto;
                position: relative;
                margin-bottom: 20px;
            }}
            
            .sidebar ul {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }}
            
            .sidebar li {{
                margin-bottom: 0;
            }}
            
            .content {{
                padding: 20px;
            }}
        }}
        
        @media (max-width: 600px) {{
            .content {{
                padding: 15px;
            }}
            
            .item {{
                padding: 15px;
            }}
        }}
    </style>
    <script>
        // Function to load checkbox states from localStorage
        function loadCheckboxStates() {{
            const checkboxes = document.querySelectorAll('.item-checkbox input[type="checkbox"]');
            checkboxes.forEach(checkbox => {{
                const itemId = checkbox.getAttribute('data-id');
                const isChecked = localStorage.getItem(itemId) === 'true';
                checkbox.checked = isChecked;
                
                // Apply checked styling
                if (isChecked) {{
                    checkbox.closest('.item').classList.add('checked');
                }}
            }});
        }}
        
        // Function to save checkbox state to localStorage
        function saveCheckboxState(event) {{
            const checkbox = event.target;
            const itemId = checkbox.getAttribute('data-id');
            localStorage.setItem(itemId, checkbox.checked);
            
            // Apply or remove checked styling
            const item = checkbox.closest('.item');
            if (checkbox.checked) {{
                item.classList.add('checked');
            }} else {{
                item.classList.remove('checked');
            }}
        }}
        
        // Navigate back to latest report
        function backToLatest() {{
            window.location.href = 'curateai_report_{today}.html';
            return false;
        }}
        
        // Initialize when the DOM is fully loaded
        document.addEventListener('DOMContentLoaded', function() {{
            loadCheckboxStates();
            
            // Add event listeners to all checkboxes
            const checkboxes = document.querySelectorAll('.item-checkbox input[type="checkbox"]');
            checkboxes.forEach(checkbox => {{
                checkbox.addEventListener('change', saveCheckboxState);
            }});
            
            // Add event listener to "Back to Latest" button
            const backBtn = document.getElementById('back-to-latest');
            if (backBtn) {{
                backBtn.addEventListener('click', backToLatest);
            }}
        }});
    </script>
</head>
<body>
    <div class="sidebar">
        <h2>CurateAI Reports</h2>
        <button id="back-to-latest" class="back-button">Back to Latest</button>
        <ul>
            <li><a href="curateai_report_{today}.html" class="active">Today ({today})</a></li>
"""
    
    # Add links to previous reports
    for date, filename in previous_reports:
        if date != today:  # Don't duplicate today's report
            html += f'            <li><a href="{filename}">{date}</a></li>\n'
    
    html += """
        </ul>
    </div>
    
    <div class="content">
        <h1>CurateAI Daily Knowledge Report</h1>
        <p class="report-date">Generated on: """ + today + """</p>
"""
    
    item_counter = 0
    for category_name, category_data in results.items():
        if category_name not in customer_config["categories"]:
            continue
            
        category_title = category_name.replace('_', ' ').title()
        category_description = customer_config["categories"][category_name]["description"]
        
        html += f"""
        <h2>{category_title}</h2>
        <p class="category-description">{category_description}</p>
"""
        
        if not category_data.get("items") or len(category_data["items"]) == 0:
            html += '        <p class="no-items">No recent items found.</p>'
            continue
            
        for item in category_data["items"]:
            item_counter += 1
            item_id = f"item-{category_name}-{item_counter}"
            
            title = item.get("title", "Untitled")
            date = item.get("date", "")
            description = item.get("description", "")
            link = item.get("link", "")
            source = item.get("source", "")
            
            html += f"""
        <div class="item" id="{item_id}">
            <div class="item-header">
                <div class="item-checkbox">
                    <input type="checkbox" data-id="{item_id}">
                </div>
                <h3>{"<a href='" + link + "' target='_blank'>" if link else ""}{title}{"</a>" if link else ""}</h3>
            </div>
            {f'<p class="date">{date}</p>' if date else ''}
            <p class="description">{description}</p>
            {f'<p class="source">Source: {source}</p>' if source else ''}
        </div>
"""
    
    html += """
    </div>
</body>
</html>"""
    
    return html

def save_report(html_content, customer_id, filename=None):
    """
    Saves the HTML report to a file.
    
    Args:
        html_content (str): HTML content to save
        customer_id (str): Customer ID
        filename (str, optional): Filename to save to. Defaults to auto-generated name.
    
    Returns:
        str: Path to the saved file
    """
    if filename is None:
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"curateai_report_{today}.html"
    
    # Create output directory if it doesn't exist
    output_dir = f"customers/{customer_id}/output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create an index.html that redirects to the latest report
    index_html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=curateai_report_{datetime.now().strftime('%Y-%m-%d')}.html">
    </head>
    <body>
        <p>Redirecting to latest report...</p>
    </body>
    </html>
    """
    
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return filepath

def send_email_report(customer_config, report_path):
    """
    Sends an email with the report to the customer.
    
    Args:
        customer_config (dict): Customer configuration
        report_path (str): Path to the report file
    """
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print(f"Email credentials not configured. Skipping email for {customer_config['customer_id']}")
        return
    
    try:
        # Read the report
        with open(report_path, "r", encoding="utf-8") as f:
            report_content = f.read()
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = customer_config['email']
        msg['Subject'] = f"Your CurateAI Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Add HTML body
        msg.attach(MIMEText(report_content, 'html'))
        
        # Send email
        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Email sent to {customer_config['email']}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")

def process_customer(customer_id):
    """
    Process a customer's report generation.
    
    Args:
        customer_id (str): Customer ID
    """
    print(f"Processing customer: {customer_id}")
    
    # Load customer configuration
    customer_config = load_customer_config(customer_id)
    
    # Get results for each category
    results = {}
    
    for category_name, category_info in customer_config["categories"].items():
        results[category_name] = get_content_for_category(category_name, category_info, customer_id)

    # Generate HTML report
    html_report = generate_html_report(results, customer_config)
    
    # Save report
    today = datetime.now().strftime("%Y-%m-%d")
    report_filename = f"curateai_report_{today}.html"
    report_path = save_report(html_report, customer_id, report_filename)
    
    # Send email if configured
    if customer_config.get("email"):
        send_email_report(customer_config, report_path)
    
    # Update last run time
    customer_config["last_run"] = datetime.now().isoformat()
    save_customer_config(customer_config)
    
    print(f"Report generated successfully for {customer_id} at: {report_path}")
    return report_path

def process_all_customers():
    """Process reports for all customers"""
    if not os.path.exists("customers"):
        print("No customers directory found. Creating it...")
        os.makedirs("customers", exist_ok=True)
        return
    
    for customer_dir in os.listdir("customers"):
        if os.path.isdir(os.path.join("customers", customer_dir)):
            try:
                process_customer(customer_dir)
            except Exception as e:
                print(f"Error processing customer {customer_dir}: {str(e)}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="CurateAI - Personalized Knowledge Curation")
    parser.add_argument("--customer", help="Process a specific customer")
    parser.add_argument("--all-customers", action="store_true", help="Process all customers")
    parser.add_argument("--add-customer", help="Add a new customer")
    parser.add_argument("--add-keywords", help="Add keywords to a customer (format: customer_id:category:keyword1,keyword2)")
    
    args = parser.parse_args()
    
    if args.customer:
        process_customer(args.customer)
    elif args.all_customers:
        process_all_customers()
    elif args.add_customer:
        customer_config = load_customer_config(args.add_customer)
        print(f"Added new customer: {args.add_customer}")
        print("Edit their configuration at:", f"customers/{args.add_customer}/config.json")
    elif args.add_keywords:
        try:
            parts = args.add_keywords.split(":", 2)
            if len(parts) != 3:
                raise ValueError("Format should be: customer_id:category:keyword1,keyword2")
            
            customer_id, category, keywords = parts
            keywords_list = [k.strip() for k in keywords.split(",")]
            
            config = load_customer_config(customer_id)
            if category not in config["categories"]:
                raise ValueError(f"Category '{category}' not found. Available categories: {', '.join(config['categories'].keys())}")
            
            for group in config["categories"][category]["keyword_groups"]:
                config["categories"][category]["keyword_groups"][group].extend(keywords_list)
                print(f"Added {len(keywords_list)} keywords to {customer_id}'s {category}/{group}")
                break
            
            save_customer_config(config)
            
        except Exception as e:
            print(f"Error adding keywords: {str(e)}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()