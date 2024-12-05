import streamlit as st
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
from tinydb import TinyDB
import json

# Load environment variables
load_dotenv()

# Initialize database
db = TinyDB('data/leads_db.json')
leads_table = db.table('leads')

# Configure API keys
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

def search_tavily_leads(keyword, country="India"):
    """Search companies using Tavily API"""
    base_url = "https://api.tavily.com/search"
    headers = {
        'Authorization': f'Bearer {TAVILY_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        "query": keyword,
        "country": country,
    }
    
    # Debugging
    #st.write("API Key:", TAVILY_API_KEY)  # Check if API Key is loaded
    #st.write("Request URL:", base_url)  # Confirm URL
    #st.write("Payload being sent:", payload)  # Confirm payload
    
    try:
        response = requests.post(base_url, headers=headers, json=payload)
        
        # Debug response
        #st.write("Response Status Code:", response.status_code)
        #st.write("Response Text:", response.text)
        
        if response.status_code == 200:
            return response.json().get('results', [])
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Error in Tavily API request: {e}")
        return []

def save_lead(lead_data):
    """Save lead information to the database"""
    lead_entry = {
        'details': lead_data,
        'timestamp': datetime.now().isoformat()
    }
    leads_table.insert(lead_entry)
    return lead_entry

def main():
    st.title("🔗 Lead Generator")
    
    # Sidebar for saved leads
    with st.sidebar:
        st.header("Saved Leads")
        if st.button("View All Leads"):
            all_leads = leads_table.all()
            for lead in all_leads:
                st.write("---")
                st.write(f"**Title:** {lead['details'].get('title', 'N/A')}")
                with st.expander("View Details"):
                    st.json(lead)
    
    # Main content
    keyword = st.text_input("Enter Keyword to Search for Companies", "")
    
    if st.button("Find Leads"):
        with st.spinner("Searching for Results..."):
            companies = search_tavily_leads(keyword)  # This now fetches the Tavily response
        
            if companies:
                st.success(f"Found {len(companies)} results")
                
                for company in companies:  # Iterating through results
                    st.write("---")
                    st.subheader(company.get('title', 'No Title'))  # Title of the result
                    st.write(f"**URL:** [Visit Website]({company.get('url', 'N/A')})")  # Link to the content
                    st.write(f"**Content Snippet:** {company.get('content', 'No content available')}")  # Content/Description
                    st.write(f"**Relevance Score:** {company.get('score', 'N/A'):.2f}")  # Relevance score
                    
                    # Save the lead
                    save_lead({
                        "title": company.get('title'),
                        "url": company.get('url'),
                        "content": company.get('content'),
                        "score": company.get('score')
                    })
            else:
                st.error("No results found. Try a different keyword.")

    if st.button("Clear All Leads"):
        leads_table.truncate()
        st.success("All saved leads have been cleared.")

if __name__ == "__main__":
    main()
