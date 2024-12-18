import streamlit as st
import os
import logging
from datetime import datetime
from tinydb import TinyDB
from tavily import TavilyClient
import openai
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize clients and database
db = TinyDB('data/leads_db.json')
leads_table = db.table('leads')
tavily_client = TavilyClient(api_key=st.secrets["TAVILY_API_KEY"])
openai.api_key = st.secrets["OPENAI_API_KEY"]

def search_tavily_leads(keyword: str, country: str = "India") -> dict:
    """Search companies using Tavily API with advanced parameters."""
    try:
        results = tavily_client.search(
            query=f"{keyword} companies in {country}",
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True,
            max_results=10
        )
        
        logger.info(f"Successfully fetched {len(results.get('results', []))} results for keyword: {keyword}")
        return results
        
    except Exception as e:
        logger.error(f"Error in Tavily search: {str(e)}")
        return {"results": [], "error": str(e)}

def summarize_leads(results: dict) -> str:
    """Generate a summary of the search results using LLM."""
    try:
        content = json.dumps(results.get('results', []), indent=2)
        
        prompt = f"""
        Analyze these company search results and provide a concise summary for each company:
        
        {content}
        
        For each company, provide:
        1. Company name
        2. Key business areas
        3. Potential opportunity
        4. Relevance score analysis
        
        Format as a clear, readable markdown list.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional assistant summarizing search results."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response["choices"][0]["message"]["content"]
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return f"Error generating summary: {str(e)}"


def generate_outreach_email(company_data: dict) -> str:
    """Generate a personalized outreach email using LLM."""
    try:
        prompt = f"""
        Generate a personalized cold outreach email from "blueoceansteels" based on the given company information:
        
        Company: {company_data.get('title')}
        Description: {company_data.get('content')}
        URL: {company_data.get('url')}
        
        Requirements:
        1. Keep it under 150 words
        2. Focus on value proposition
        3. Include a clear call to action
        4. Be professional but conversational
        5. Reference specific company details
        
        Format the email with subject line and body.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an assistant that writes professional emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85
        )
        
        return response["choices"][0]["message"]["content"]
        
    except Exception as e:
        logger.error(f"Error generating email: {str(e)}")
        return f"Error generating email: {str(e)}"

def save_lead(lead_data: dict) -> dict:
    """Save lead information to the database."""
    try:
        lead_entry = {
            'details': lead_data,
            'timestamp': datetime.now().isoformat()
        }
        leads_table.insert(lead_entry)
        logger.info(f"Successfully saved lead: {lead_data.get('title')}")
        return lead_entry
        
    except Exception as e:
        logger.error(f"Error saving lead: {str(e)}")
        return {"error": str(e)}

def main():
    st.title("Lead Generator Pro")
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'generated_emails' not in st.session_state:
        st.session_state.generated_emails = {}
    if 'saved_leads' not in st.session_state:
        st.session_state.saved_leads = set()

    # Sidebar for saved leads
    with st.sidebar:
        st.header("📋 Saved Leads")
        if st.button("View All Leads"):
            all_leads = leads_table.all()
            st.dataframe(
                [{"Title": lead['details'].get('title', 'N/A'), 
                  "Score": lead['details'].get('score', 'N/A'),
                  "Date": lead['timestamp']} for lead in all_leads]
            )
    
    # Main content
    col1, col2 = st.columns([2, 1])
    with col1:
        keyword = st.text_input("🔍 Enter Keywords to Search Companies", "")
    with col2:
        country = st.selectbox("🌍 Select Country", ["India", "USA", "UK", "Singapore"])
    
    # Search button
    if st.button("🚀 Find Leads"):
        if not keyword:
            st.error("Please enter a keyword to search.")
            return

        with st.spinner("Searching for companies..."):
            st.session_state.results = search_tavily_leads(keyword, country)
            
            if st.session_state.results.get('results'):
                with st.spinner("Analyzing results..."):
                    summary = summarize_leads(st.session_state.results)
                    st.markdown(summary)
            else:
                st.error("No results found.")

    # Display results if available
    if st.session_state.results and st.session_state.results.get('results'):
        st.subheader("📊 Detailed Results")
        for idx, company in enumerate(st.session_state.results['results']):
            with st.expander(f"🏢 {company.get('title', 'Company')}"):
                st.write(f"**Relevance Score:** {company.get('score', 'N/A')}")
                st.write(f"**URL:** [{company.get('url')}]({company.get('url')})")
                st.write(f"**Description:** {company.get('content')}")
                
                email_key = f"email_{idx}"
                save_key = f"save_{idx}"
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if st.button("📧 Generate Email", key=email_key):
                        email = generate_outreach_email(company)
                        st.session_state.generated_emails[email_key] = email
                
                with col2:
                    if st.button("💾 Save Lead", key=save_key):
                        save_lead(company)
                        st.session_state.saved_leads.add(save_key)
                        st.success("Lead saved successfully!")

                # Display generated email
                if email_key in st.session_state.generated_emails:
                    st.markdown("### Generated Email:")
                    st.markdown(st.session_state.generated_emails[email_key])

    # Clear all button
    if st.button("🗑️ Clear All"):
        leads_table.truncate()
        st.session_state.clear()
        st.success("All data cleared successfully!")


if __name__ == "__main__":
    main()
