"""
Plurality Knowledge Bot

This script uses the Perplexity API to fetch the latest information about
organizations, researchers, papers, events, and jobs relevant to Plurality Institute.
It can be scheduled to run daily using cron, GitHub Actions, or any scheduler.

Usage:
  python plurality_knowledge_bot.py
"""
import requests
import json
import os
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("PERPLEXITY_API_KEY")
if not API_KEY:
    raise ValueError("Please set the PERPLEXITY_API_KEY environment variable")

# Define keyword groups to manage API requests better
PEOPLE_KEYWORDS = [
    "Alessandra Casella", "Allison Duettmann", "Allison Stanger", "Audrey Tang",
    "Aviv Ovadya", "Beth Noveck", "Bill Doherty", "Bruce Schneier", "CL Kao",
    "Charlotte Cavaillé", "Colin Megill", "Cory Doctorow", "Danielle Allen",
    "Daron Acemoglu", "David Bloomin", "Deb Roy", "Deepti Doshi", "Dimitrios Xefteris",
    "Divya Siddarth", "Edward Casternova", "Eli Pariser", "Eric A. Posner",
    "Eugene Leventhal", "Evan Miyazono", "Glen Weyl", "Helen Nissenbaum",
    "James Evans", "Jamie Joyce", "Jeffrey Fossett", "John Etchemendy",
    "Jon X. Eguia", "Joshua Tan", "Juan Benet", "Kevin Owocki", "Lisa Schirch",
    "Madeleine Daepp", "Mahnaz Roshanaei", "Manon Revel", "Margaret Levi",
    "Matthew Prewitt", "Mike Jordan", "Nathan Schneider", "Nicole Immorlica",
    "Percy Liang", "Primavera De Filippi", "Puja Ohlhaver", "Rob Reich",
    "Rose Bloomin", "Saffron Huang", "Shrey Jain", "Stefaan Verhulst",
    "Uma Viswanathan", "Uri Wilensky", "Victor Lange", "Vitalik Buterin",
    "Wes Chao", "Zoë Hitzig", "danah boyd"
]

# Define key people for "Our People" section (to be implemented later)
KEY_PEOPLE = [
    "Glen Weyl", "Divya Siddarth", "Audrey Tang", "Joshua Tan", 
    "Matt Prewitt", "E. Glen Weyl", "Puja Ohlhaver"
]

ORGANIZATION_KEYWORDS = [
    "Plurality Institute", "Berkman Klein Center for Internet & Society",
    "Harvard Democracy Renovation Lab", "MIT Media Lab",
    "Stanford Center for AI Governance and Policy", "Y Combinator Research",
    "OpenAI", "Anthropic", "Meta Government", "Civic Tech Field Guide",
    "New Public", "Public Interest Tech", "Tech for Good", "All Tech is Human",
    "RadicalX", "AI and Democracy Foundation", 
    "Microsoft Plural Technology Collaboratory", 
    "University of California, Berkeley CHAI", "Gitcoin",
    "Tech Policy Press"
]

CONCEPT_KEYWORDS = [
    "collective intelligence", "digital democracy", "collaborative governance",
    "distributed systems", "decentralized autonomous organizations", "plurality",
    "digital commons", "pluralism", "tech ethics", "tech policy", 
    "AI ethics", "AI governance", "AI policy", "AI regulation",
    "decentralized governance"
]

# Define the categories with their keyword groups
PLURALITY_CATEGORIES = {
    "research_papers": {
        "description": "Recent academic papers and publications",
        "keyword_groups": {
            "concepts": CONCEPT_KEYWORDS,
            "people": PEOPLE_KEYWORDS,
            "organizations": ORGANIZATION_KEYWORDS
        }
    },
    "industry_news": {
        "description": "Latest news and developments",
        "keyword_groups": {
            "concepts": CONCEPT_KEYWORDS,
            "people": PEOPLE_KEYWORDS,
            "organizations": ORGANIZATION_KEYWORDS
        }
    },
    "events": {
        "description": "Upcoming conferences, events, workshops, talks, virtual events, panels, panel discussions, and meetups",
        "keyword_groups": {
            "events": [
                "plurality conference", "digital democracy workshop",
                "collective intelligence symposium", "governance innovation",
                "tech ethics", "tech policy", "tech policy press",
                "tech policy conference", "tech policy workshop",
                "tech policy symposium", "tech policy panel",
                "tech policy panel discussion", "tech policy meetup",
                "AI ethics talk", "AI ethics symposium"
            ]
        }
    },
    "jobs": {
        "description": "Job opportunities, fellowships, grants, research funding and positions",
        "keyword_groups": {
            "jobs": [
                "plurality researcher", "digital democracy",
                "collective intelligence", "tech ethics researcher",
                "governance innovation", "All Tech is Human", "tech policy",
                "Tech For Good", "AI Safety", "AI Ethics", "AI Governance",
                "AI Policy", "AI Regulation", "Gitcoin Grants", "RadicalX",
                "New_ public"
            ]
        }
    }
}

def get_plurality_updates_for_group(category_name, group_name, keywords):
    """
    Fetches latest updates for a specific keyword group using Perplexity API.
    
    Args:
        category_name (str): Name of the category
        group_name (str): Name of the keyword group
        keywords (list): List of keywords to search for
        
    Returns:
        dict: Structured information about the latest updates
    """
    url = "https://api.perplexity.ai/chat/completions"
    
    # Limit the number of keywords per request to avoid token limits
    # Split into chunks of max 15 keywords
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
        
        category_description = PLURALITY_CATEGORIES[category_name]["description"]
        
        prompt = f"""You are a content curator for Plurality Institute that sources jobs, events, research papers, media and other information.
        Find {category_description} related to the following keywords:
        {keywords_str}

        Include titles, dates, brief descriptions, links, and sources.
         Format your response as a JSON object with the following structure:
{{
  "items": [
    {{
      "title": "Item title",
      "date": "Publication date if available",
      "description": "Brief description (50 words max)",
      "link": "URL if available",
      "source": "Source name"
    }}
  ]
}}

Only include highly relevant items from the past 3 months (since December 2024)" Prioritize reputable sources.
Do NOT include any content from plurality.institute or the Plurality Institute's own website.
Articles and news must be published after December 1, 2024! Events must be happening after March 11, 2025. 
Include information from academic journals, podcasts, relevant substack blogs, LinkedIn, news sites, X.com, Bsky, conference websites, job boards, Luma(an event website) and social media as appropriate. Do not include information for events that have already occurred or opportunities that have already ended.
For jobs(grants, fellowships, research funding, etc), only include opportunities that are currently active and accepting applications. We want a LOT of opportunities, so don't be too picky on this part. Be sure to try to include 2-3 opportunities.
For events, we want a lot of events so don't be too picky. As long as they are tangentially related and happening soon, include them! Feel free to include events happening from March, 2025 through January, 2026. 
"""
        
        data = {
            "model": "sonar-pro",  # Using Perplexity's most capable model
            "messages": [
                {
                    "role": "system",
                    "content": "You are a specialized research assistant and content curator for Plurality Institute, focused on finding and summarizing the latest relevant information."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.2  # Lower temperature for more factual responses
        }
        
        try:
            print(f"  Making API request for {category_name}/{group_name} (chunk of {len(chunk)} keywords)...")
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse the JSON response
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
        
        # Add a delay between API calls to avoid rate limiting
        time.sleep(2)
    
    return {"items": all_items}


def get_plurality_updates(category_name, category_info):
    """
    Fetches latest updates for all keyword groups in a category, combining results.
    
    Args:
        category_name (str): Name of the category
        category_info (dict): Dictionary with category description and keyword groups
        
    Returns:
        dict: Combined results from all keyword groups
    """
    print(f"Processing category: {category_name}...")
    all_items = []
    
    # Process each keyword group separately
    for group_name, keywords in category_info["keyword_groups"].items():
        group_results = get_plurality_updates_for_group(category_name, group_name, keywords)
        if "items" in group_results:
            all_items.extend(group_results["items"])
    
    # Remove duplicate items based on title
    unique_items = []
    seen_titles = set()
    
    for item in all_items:
        title = item.get("title", "").strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_items.append(item)
    
    print(f"Found {len(unique_items)} unique items for {category_name}")
    return {"items": unique_items}

def get_previous_reports(max_reports=10):
    """
    Get a list of previous reports in the output directory.
    
    Args:
        max_reports (int): Maximum number of previous reports to include
        
    Returns:
        list: List of tuples (date, filename) of previous reports
    """
    import os
    import re
    
    reports = []
    
    # Check if the output directory exists
    if not os.path.exists("output"):
        return reports
    
    # Pattern to match report filenames (plurality_report_YYYY-MM-DD.html)
    pattern = r"plurality_report_(\d{4}-\d{2}-\d{2})\.html"
    
    for filename in os.listdir("output"):
        match = re.match(pattern, filename)
        if match:
            date = match.group(1)
            reports.append((date, filename))
    
    # Sort by date (newest first)
    reports.sort(reverse=True)
    
    # Limit the number of reports
    return reports[:max_reports]

def generate_html_report(results):
    """
    Generates an HTML report from the collected results, including a sidebar for previous reports.
    
    Args:
        results (dict): Dictionary mapping categories to their results
        
    Returns:
        str: HTML content of the report
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get the list of previous reports
    previous_reports = get_previous_reports()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plurality Daily Knowledge Report - {today}</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f9f9f9;
            display: flex;
            min-height: 100vh;
        }}
        
        .sidebar {{
            width: 250px;
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }}
        
        .sidebar h2 {{
            color: white;
            border-bottom: 1px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        
        .sidebar ul {{
            list-style: none;
            padding: 0;
        }}
        
        .sidebar li {{
            margin-bottom: 8px;
        }}
        
        .sidebar a {{
            color: #ecf0f1;
            text-decoration: none;
            display: block;
            padding: 5px;
            border-radius: 4px;
        }}
        
        .sidebar a:hover {{
            background-color: #34495e;
        }}
        
        .sidebar a.active {{
            background-color: #3498db;
            font-weight: bold;
        }}
        
        .content {{
            flex: 1;
            padding: 20px;
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        
        h2 {{
            color: #2c3e50;
            border-left: 4px solid #3498db;
            padding-left: 10px;
            margin-top: 25px;
        }}
        
        .item {{
            background-color: white;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 15px;
            margin-bottom: 15px;
        }}
        
        .item h3 {{
            color: #3498db;
            margin-top: 0;
        }}
        
        .item p {{
            margin: 5px 0;
        }}
        
        .date {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        .source {{
            color: #7f8c8d;
            font-size: 0.9em;
            text-align: right;
        }}
        
        .description {{
            margin: 10px 0;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .report-date {{
            text-align: right;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 10px;
        }}
        
        .category-description {{
            font-style: italic;
            color: #555;
            margin-bottom: 15px;
        }}
        
        .no-items {{
            font-style: italic;
            color: #7f8c8d;
            padding: 10px;
        }}
        
        /* Responsive adjustments */
        @media (max-width: 768px) {{
            body {{
                flex-direction: column;
            }}
            
            .sidebar {{
                width: 100%;
                height: auto;
                position: relative;
            }}
            
            .content {{
                padding: 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>Plurality Reports</h2>
        <ul>
            <li><a href="plurality_report_{today}.html" class="active">Today ({today})</a></li>
"""
    
    # Add links to previous reports
    for date, filename in previous_reports:
        html += f'            <li><a href="{filename}">{date}</a></li>\n'
    
    html += """
        </ul>
    </div>
    
    <div class="content">
        <h1>Plurality Institute Daily Knowledge Report</h1>
        <p class="report-date">Generated on: """ + today + """</p>
"""
    
    # Add each category to the HTML
    for category_name, category_data in results.items():
        category_title = category_name.replace('_', ' ').title()
        category_description = PLURALITY_CATEGORIES[category_name]["description"]
        
        html += f"""
        <h2>{category_title}</h2>
        <p class="category-description">{category_description}</p>
"""
        
        if not category_data.get("items") or len(category_data["items"]) == 0:
            html += '        <p class="no-items">No recent items found.</p>'
            continue
            
        for item in category_data["items"]:
            title = item.get("title", "Untitled")
            date = item.get("date", "")
            description = item.get("description", "")
            link = item.get("link", "")
            source = item.get("source", "")
            
            html += f"""
        <div class="item">
            <h3>{"<a href='" + link + "' target='_blank'>" if link else ""}{title}{"</a>" if link else ""}</h3>
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

def save_report(html_content, filename=None):
    """
    Saves the HTML report to a file.
    
    Args:
        html_content (str): HTML content to save
        filename (str, optional): Filename to save to. Defaults to auto-generated name.
    
    Returns:
        str: Path to the saved file
    """
    if filename is None:
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"plurality_report_{today}.html"
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    filepath = os.path.join("output", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return filepath

def main():
    """Main function that runs the Plurality Knowledge Bot."""
    print("Starting Plurality Knowledge Bot...")
    print(f"Gathering information for {len(PLURALITY_CATEGORIES)} categories...")
    
    results = {}
    
    # Process each category
    for category_name, category_info in PLURALITY_CATEGORIES.items():
        results[category_name] = get_plurality_updates(category_name, category_info)
    
    # Generate and save the HTML report
    html_report = generate_html_report(results)
    
    # Save with date-specific filename
    today = datetime.now().strftime("%Y-%m-%d")
    report_filename = f"plurality_report_{today}.html"
    report_path = save_report(html_report, report_filename)
    
    # Also save to index.html to always have the latest report accessible at a fixed URL
    index_path = save_report(html_report, "index.html")
    
    print(f"Report generated successfully at: {report_path}")
    print(f"Latest report also saved to: {index_path}")

if __name__ == "__main__":
    main()