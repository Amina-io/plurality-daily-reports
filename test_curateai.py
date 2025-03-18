import os
import json
from curateai import load_customer_config, save_customer_config, process_customer

# Create test customer
customer_id = "test001"
config = load_customer_config(customer_id)

# Add test keywords
config["name"] = "Test Customer"
config["email"] = "test@example.com"
config["categories"]["research_papers"]["keyword_groups"]["concepts"] = ["artificial intelligence", "machine learning"]
config["categories"]["industry_news"]["keyword_groups"]["organizations"] = ["Google", "OpenAI"]
config["categories"]["events"]["keyword_groups"]["events"] = ["AI conference", "tech summit"]
config["categories"]["jobs"]["keyword_groups"]["jobs"] = ["machine learning engineer", "AI researcher"]

# Save the updated config
save_customer_config(config)

# Process the customer
report_path = process_customer(customer_id)
print(f"Test report generated at: {report_path}")
print("Open this file in a browser to view the report")