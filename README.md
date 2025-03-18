# Plurality Knowledge Bot

A daily knowledge gathering tool for Plurality Institute that automatically collects and presents the latest information on research papers, industry news, events, and job opportunities relevant to Plurality Institute's focus areas.

## Features

- Automatically gathers information from multiple sources using Perplexity's AI
- Focuses on key people, organizations, and topics in the Plurality ecosystem
- Categorizes information into research papers, industry news, events, and opportunities
- Generates a beautiful HTML report with all collected information
- Implements deduplication to avoid repeating content
- Prioritizes recency while ensuring sufficient content
- Daily scheduled runs via GitHub Actions

## Setup Instructions

1. Clone this repository
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Perplexity API key:
   ```
   PERPLEXITY_API_KEY=your_api_key_here
   ```
4. Run the knowledge bot:
   ```
   python plurality_knowledge_bot.py
   ```

## Key Components

The script has several key components:

1. **Key People, Organizations, and Topics**: The script focuses on important figures and organizations in the Plurality ecosystem.

2. **Category Definitions**: Information is categorized into:
   - Research papers
   - Industry news
   - Events
   - Opportunities (jobs, grants, fellowships)

3. **Result Deduplication**: A hashing system prevents the same content from appearing in multiple reports.

4. **HTML Report Generation**: Creates a clean, responsive HTML report of the findings.

## Customization

You can customize the bot by modifying:

- `KEY_PEOPLE`, `KEY_ORGANIZATIONS`, and `KEY_TOPICS` lists to change search focus
- `PLURALITY_CATEGORIES` dictionary to adjust category keywords and descriptions  
- `HTML_TEMPLATE` to change the report appearance
- `DAYS_TO_LOOK_BACK` constant to adjust the time window for searches

## Automation with GitHub Actions

This repository includes a GitHub Actions workflow file (`.github/workflows/daily-report.yml`) that:

1. Runs the script daily at 6 AM PST
2. Commits and pushes any changes to the report
3. Can be triggered manually through the Actions tab

To use GitHub Actions:

1. Add your `PERPLEXITY_API_KEY` as a repository secret in your GitHub repo settings
2. Ensure the workflow file is in the correct location
3. Enable Actions for your repository

## Output

The script generates HTML reports in the `output` directory:

- `plurality_report_YYYY-MM-DD.html`: Daily dated reports
- `index.html`: Always contains the latest report
- `previous_results.json`: Tracks previously seen content to avoid duplication

## Example Report Structure

Each report includes:

- **Research Papers**: Academic papers and publications
- **Industry News**: Recent news and developments
- **Events**: Upcoming events, conferences, and webinars
- **Opportunities**: Job openings, grants, fellowships, and other opportunities

## Extending the Tool

You can extend this tool by:

1. Adding email notifications to team members when new reports are generated
2. Deploying the reports to a static website hosted on Vercel or GitHub Pages
3. Adding more advanced filters or search techniques
4. Implementing automated social media sharing of key findings
5. Creating a simple web interface to browse historical reports
