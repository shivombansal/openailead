import streamlit as st
import os
from dotenv import load_dotenv
import requests
from litellm import completion
from datetime import datetime
from tinydb import TinyDB, Query
import json

# Load environment variables
load_dotenv()

# Initialize database
db = TinyDB('data/leads_db.json')
leads_table = db.table('leads')
prompts_table = db.table('prompts')

# Configure API keys
PROXYCURL_API_KEY = os.getenv('PROXYCURL_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def get_linkedin_profile(linkedin_url):
   """Fetch LinkedIn profile data using ProxyCurl API"""
   api_endpoint = 'https://nubela.co/proxycurl/api/v2/linkedin'
   headers = {'Authorization': f'Bearer {PROXYCURL_API_KEY}'}
   params = {
       'url': linkedin_url,
       'use_cache': 'if-present',
   }
  
   response = requests.get(api_endpoint, params=params, headers=headers)
   if response.status_code == 200:
       return response.json()
   return None

def analyze_lead(profile_data):
   """Analyze lead using OpenAI API through LiteLLM"""
   prompt = f"""
   Analyze the following LinkedIn profile data and categorize the lead as HOT, WARM, or COLD.
   Also provide a brief explanation and a personalized outreach message.
  
   Profile Data:
   {json.dumps(profile_data, indent=2)}
  
   Provide response in the following JSON format:
   {{
       "category": "HOT/WARM/COLD",
       "explanation": "Brief explanation",
       "outreach_message": "Personalized message"
   }}
   """
  
   response = completion(
       model="gpt-3.5-turbo",
       messages=[{"role": "user", "content": prompt}],
       api_key=OPENAI_API_KEY
   )
  
   return json.loads(response.choices[0].message.content)

def save_lead(profile_data, analysis):
   """Save lead information to database"""
   lead_data = {
       'profile': profile_data,
       'analysis': analysis,
       'timestamp': datetime.now().isoformat()
   }
   leads_table.insert(lead_data)
   return lead_data

def main():
   st.title("🎯 Lead Generation AI")
  
   # Sidebar for viewing saved leads
   with st.sidebar:
       st.header("Saved Leads")
       if st.button("View All Leads"):
           all_leads = leads_table.all()
           for lead in all_leads:
               st.write("---")
               st.write(f"**Timestamp:** {lead['timestamp']}")
               st.write(f"**Category:** {lead['analysis']['category']}")
               with st.expander("View Details"):
                   st.json(lead)
  
   # Main content
   linkedin_url = st.text_input("Enter LinkedIn Profile URL")
  
   if st.button("Analyze Lead"):
       with st.spinner("Fetching profile data..."):
           profile_data = get_linkedin_profile(linkedin_url)
          
           if profile_data:
               st.success("Profile data fetched successfully!")
              
               with st.spinner("Analyzing lead..."):
                   analysis = analyze_lead(profile_data)
                  
                   # Display results
                   st.header("Analysis Results")
                  
                   category_color = {
                       "HOT": "🔴",
                       "WARM": "🟡",
                       "COLD": "🔵"
                   }
                  
                   st.subheader(f"Lead Category: {category_color.get(analysis['category'], '⚪')} {analysis['category']}")
                   st.write(f"**Explanation:** {analysis['explanation']}")
                  
                   st.text_area("Suggested Outreach Message", analysis['outreach_message'], height=200)
                  
                   # Save lead
                   save_lead(profile_data, analysis)
                   st.success("Lead information saved to database!")
           else:
               st.error("Failed to fetch profile data. Please check the URL and try again.")


if __name__ == "__main__":
       main()
       
