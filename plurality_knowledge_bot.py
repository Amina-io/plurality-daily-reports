#!/usr/bin/env python3
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
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Store your API key securely
API_KEY = os.environ.get("PERPLEXITY_API_KEY")
if not API_KEY:
    raise ValueError("Please set the PERPLEXITY_API_KEY environment variable")

# Define the categories and keywords
PLURALITY_CATEGORIES = {
    "research_papers": {
        "description": "Recent academic papers and publications",
        "keywords": [
            "collective intelligence", 
            "digital democracy",
            "collaborative governance",
            "distributed systems",
            "decentralized autonomous organizations",
            "plurality",
            "digital commons"
        ]
    },
    "industry_news": {
        "description": "Latest news and developments",
        "keywords": [
            "plurality project",
            "digital democracy",
            "collective intelligence platforms",
            "decentralized governance",
            "tech policy",
            "digital commons"
        ]
    },
    "events": {
        "description": "Upcoming conferences, workshops, and meetups",
        "keywords": [
            "plurality conference",
            "digital democracy workshop",
            "collective intelligence symposium",
            "governance innovation",
            "tech ethics"
        ]
    },
    "jobs": {
        "description": "Job opportunities and positions",
        "keywords": [
            "plurality researcher",
            "digital democracy",
            "collective intelligence",
            "tech ethics researcher",
            "governance innovation"
        ]
    }
}

def get_plurality_updates(category_name, category_info):
    """
    Fetches latest updates about given keywords in the specified category using Perplexity API.
    
    Args:
        category_name (str): Name of the category
        category_info (dict): Dictionary with category description and keywords
        
    Returns:
        dict: Structured information about the latest updates
    """
    url = "https://api.perplexity.ai/chat/completions"
    
    keywords_str = ", ".join(category_info["keywords"])
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""You are a research assistant for Plurality Institute.
    Provide the latest {category_name.replace('_', ' ')} related to the following keywords from the past 48 hours:
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
    
    Only include highly relevant and recent items. Prioritize reputable sources.
    If you find fewer than 3 items, expand your search to the past week.
    Include information from academic journals, news sites, conference websites, job boards, and social media as appropriate.
    """
    
    data = {
        "model": "sonar-pro",  # Using Perplexity's most capable model
        "messages": [
            {
                "role": "system",
                "content": "You are a specialized research assistant for Plurality Institute, focused on finding and summarizing the latest relevant information."
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
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Parse the JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print(f"Error parsing JSON response for {category_name}. Raw response:")
            print(content)
            return {"items": []}
            
    except requests.exceptions.RequestException as e:
        print(f"Error making API request for {category_name}: {str(e)}")
        return {"items": []}
    except (KeyError, IndexError) as e:
        print(f"Error parsing API response for {category_name}: {str(e)}")
        return {"items": []}
    except Exception as e:
        print(f"Unexpected error for {category_name}: {str(e)}")
        return {"items": []}

def generate_html_report(results):
    """
    Generates an HTML report from the collected results.
    
    Args:
        results (dict): Dictionary mapping categories to their results
        
    Returns:
        str: HTML content of the report
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
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
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-top: 30px;
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
    </style>
</head>
<body>
    <h1>Plurality Institute Daily Knowledge Report</h1>
    <p class="report-date">Generated on: {today}</p>
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
            html += '<p class="no-items">No recent items found.</p>'
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
    
    # Process each category with a slight delay to avoid API rate limits
    for category_name, category_info in PLURALITY_CATEGORIES.items():
        print(f"Processing category: {category_name}...")
        results[category_name] = get_plurality_updates(category_name, category_info)
        time.sleep(2)  # Small delay between API calls
    
    # Generate and save the HTML report
    html_report = generate_html_report(results)
    report_path = save_report(html_report)
    
    print(f"Report generated successfully at: {report_path}")
    
    # Optionally, you could add code here to:
    # 1. Email the report to team members
    # 2. Upload to a web server
    # 3. Commit to a GitHub Pages repository
    # 4. etc.

if __name__ == "__main__":
    main()