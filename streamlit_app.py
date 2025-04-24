import streamlit as st
import requests
import json
import time

# Page configuration
st.set_page_config(
    page_title="Lithuanian Market Product Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Title and description
st.title("🔍 Lithuanian Market Product Analyzer")
st.markdown("""
This application analyzes Lithuanian market products based on a technical specification.
It queries the Perplexity API to gather structured product information and evaluates each product.
""")

# Check if API key is configured
if 'perplexity_api_key' not in st.secrets.get("config", {}):
    st.error("""
    ⚠️ Perplexity API key not found in secrets.

    1. Create a `.streamlit/secrets.toml` file with your Perplexity API key:
    ```
    [config]
    perplexity_api_key = "your_perplexity_api_key"
    ```

    2. Restart the application.
    """)
    st.stop()

# Get the API key from secrets
PERPLEXITY_API_KEY = st.secrets["config"]["perplexity_api_key"]

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["Product Search", "Search History", "About"])

with tab1:
    st.header("Search for Products")

    # Technical specification input
    st.subheader("Enter Technical Specification")
    tech_spec = st.text_area(
        "Technical specifications for the product you're looking for:",
        height=200,
        placeholder="Example: Smartphone with at least 6GB RAM, 128GB storage, 6.1 inch OLED display, 5G connectivity, IP68 water resistance"
    )


    # Improved prompt template
    def generate_prompt(tech_spec):
        return f"""Analyze the Lithuanian market and gather detailed product information according to the following technical specification:
{tech_spec}

Follow these guidelines:
1. Tik Lietuviški puslapiai (išskyrus katalogas.cpo.lt, zuza.lt)
2. Verify the product is currently available for purchase
3. Gather accurate pricing in EUR
4. Evaluate technical specification requirements one by one

IMPORTANT: Your response MUST be formatted EXACTLY as a valid JSON array of product objects.
Each product in the array should have the following fields:

[
  {{
    "provider": "Company selling the product",
    "provider_website": "Main website domain (e.g., telia.lt)",
    "provider_url": "Full URL to the specific product page",
    "product_name": "Complete product name with model",
    "product_properties": {{
      "key_spec1": "value1",
      "key_spec2": "value2"
    }},
    "product_sku": "Any product identifiers (SKU, UPC, model number)",
    "product_price": 299.99,
    "evaluation": "Detailed assessment of how the product meets or fails each technical specification"
  }}
]

DO NOT include any explanation, preamble, or additional text - ONLY provide the JSON array.
"""


    # Function to query Perplexity API
    def query_perplexity(prompt, api_key):
        url = "https://api.perplexity.ai/chat/completions"

        payload = {
            "model": "sonar-pro",
            "search_domain_filter": [
                "vaistai.lt",
                "kainos.lt",
                "kaina24.lt",
                "gintarine.lt",
                "eurovaistine.lt",
                "manovaistine.lt",
                # "-zuza.lt",
                # "-katalogas.cpo.lt"
            ],
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant specialized in Lithuanian market product analysis. Your responses should be accurate, structured as requested, and focused on product information available in Lithuania. Always format product data as proper JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2
            # Removed the response_format parameter which was causing the error
        }

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}"
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API request failed with status code {response.status_code}: {response.text}"}


    # Function to parse and display results
    def display_results(response_data):
        if "error" in response_data:
            st.error(f"Error: {response_data['error']}")
            return

        try:
            # Extract the content from the Perplexity response
            content = response_data["choices"][0]["message"]["content"]

            # Display raw response for debugging
            with st.expander("View Raw API Response"):
                st.text(content)

            # Extract JSON from the response
            # Try to find JSON within the text (in case it's wrapped in text)
            import re
            json_match = re.search(r'(\[\s*{.*}\s*\]|\{\s*"products"\s*:\s*\[.*\]\s*\})', content, re.DOTALL)

            if json_match:
                json_str = json_match.group(0)
                try:
                    products_data = json.loads(json_str)
                except:
                    # If that fails, try to parse the entire content
                    products_data = json.loads(content)
            else:
                # If no JSON pattern found, try parsing the entire content
                products_data = json.loads(content)

            # Check if the response is directly a list or if it contains a 'products' key
            if isinstance(products_data, dict) and "products" in products_data:
                products = products_data["products"]
            else:
                products = products_data

            if not isinstance(products, list):
                st.error("The response format is not as expected. Please try again.")
                st.json(products_data)
                return

            # Display the products
            st.subheader(f"Found {len(products)} Products")

            # Save to session state history
            if "search_history" not in st.session_state:
                st.session_state.search_history = []

            history_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tech_spec": tech_spec,
                "results": products
            }
            st.session_state.search_history.append(history_entry)

            # Display results in expandable sections
            for i, product in enumerate(products):
                with st.expander(
                        f"{i + 1}. {product.get('product_name', 'Unknown Product')} - €{product.get('product_price', 'N/A')}"):
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.markdown(f"**Provider:** {product.get('provider', 'N/A')}")
                        st.markdown(f"**Website:** {product.get('provider_website', 'N/A')}")
                        if 'provider_url' in product and product['provider_url']:
                            st.markdown(f"**Product Link:** [View Product]({product['provider_url']})")
                        st.markdown(f"**SKU/ID:** {product.get('product_sku', 'N/A')}")
                        st.markdown(f"**Price:** €{product.get('product_price', 'N/A')}")

                    with col2:
                        st.subheader("Product Properties")
                        properties = product.get('product_properties', {})
                        if properties:
                            for key, value in properties.items():
                                st.markdown(f"**{key}:** {value}")
                        else:
                            st.write("No detailed properties available.")

                        st.subheader("Technical Evaluation")
                        evaluation = product.get('evaluation', 'No evaluation available.')
                        st.write(evaluation)

            # Show raw JSON option
            with st.expander("View Raw JSON Response"):
                st.json(products)

        except json.JSONDecodeError as json_err:
            st.error("Failed to parse the JSON response from the API.")
            st.write("Attempting to extract JSON from the response...")

            # Try to find and extract JSON from text with a more aggressive approach
            try:
                import re
                # Look for anything that might be JSON
                json_pattern = r'(\[[\s\S]*\]|\{[\s\S]*\})'
                matches = re.findall(json_pattern, content)

                if matches:
                    st.write(f"Found {len(matches)} potential JSON structures. Trying to parse them...")

                    for i, match in enumerate(matches):
                        try:
                            potential_json = json.loads(match)
                            st.success(f"Successfully parsed JSON structure #{i + 1}")

                            # If we have a valid JSON structure, try to display it
                            if isinstance(potential_json, list):
                                products = potential_json
                                st.success(f"Found a list of {len(products)} products! Displaying results...")
                                break
                            elif isinstance(potential_json, dict) and "products" in potential_json:
                                products = potential_json["products"]
                                st.success(f"Found a dictionary with {len(products)} products! Displaying results...")
                                break
                        except:
                            st.write(f"Structure #{i + 1} is not valid JSON.")

                    # If we found and successfully parsed JSON with products
                    if 'products' in locals() and isinstance(products, list) and len(products) > 0:
                        # Continue with displaying products
                        pass
                    else:
                        # No valid JSON product list found
                        st.error("Could not extract a valid product list from the response.")
                        st.text("Raw content:")
                        st.text(content)
                else:
                    st.error("No JSON-like structures found in the response.")
                    st.text("Raw content:")
                    st.text(content)
            except Exception as extract_err:
                st.error(f"Error while trying to extract JSON: {str(extract_err)}")
                st.text("Raw content:")
                st.text(content)
        except Exception as e:
            st.error(f"An error occurred while processing the results: {str(e)}")
            st.text("Response data:")
            st.write(response_data)


    # Search button
    if st.button("Search Products", type="primary", disabled=not tech_spec):
        with st.spinner("Analyzing Lithuanian market products... (this may take 30-60 seconds)"):
            prompt = generate_prompt(tech_spec)

            # Show prompt in expandable section
            with st.expander("View Search Prompt"):
                st.text(prompt)

            # Query the API
            response = query_perplexity(prompt, PERPLEXITY_API_KEY)

            # Display results
            display_results(response)

with tab2:
    st.header("Search History")

    if "search_history" not in st.session_state or not st.session_state.search_history:
        st.info("No search history yet. Search for products to see your history here.")
    else:
        for i, entry in enumerate(reversed(st.session_state.search_history)):
            with st.expander(f"{entry['timestamp']} - {entry['tech_spec'][:50]}..."):
                st.markdown(f"**Search Query:**\n{entry['tech_spec']}")
                st.markdown(f"**Results:** {len(entry['results'])} products found")

                # Display results again
                for j, product in enumerate(entry['results']):
                    st.markdown(
                        f"**{j + 1}. {product.get('product_name', 'Unknown Product')}** - €{product.get('product_price', 'N/A')}")
                    st.markdown(
                        f"Provider: {product.get('provider', 'N/A')} | [View Product]({product.get('provider_url', '#')})")

                # Option to view full details
                if st.button(f"View Full Details #{i}", key=f"history_{i}"):
                    # This recreates the detailed view from the Search tab
                    for j, product in enumerate(entry['results']):
                        with st.expander(
                                f"{j + 1}. {product.get('product_name', 'Unknown Product')} - €{product.get('product_price', 'N/A')}"):
                            col1, col2 = st.columns([1, 2])

                            with col1:
                                st.markdown(f"**Provider:** {product.get('provider', 'N/A')}")
                                st.markdown(f"**Website:** {product.get('provider_website', 'N/A')}")
                                if 'provider_url' in product and product['provider_url']:
                                    st.markdown(f"**Product Link:** [View Product]({product['provider_url']})")
                                st.markdown(f"**SKU/ID:** {product.get('product_sku', 'N/A')}")
                                st.markdown(f"**Price:** €{product.get('product_price', 'N/A')}")

                            with col2:
                                st.subheader("Product Properties")
                                properties = product.get('product_properties', {})
                                if properties:
                                    for key, value in properties.items():
                                        st.markdown(f"**{key}:** {value}")
                                else:
                                    st.write("No detailed properties available.")

                                st.subheader("Technical Evaluation")
                                evaluation = product.get('evaluation', 'No evaluation available.')
                                st.write(evaluation)

with tab3:
    st.header("About This Application")

    st.markdown("""
    ## Lithuanian Market Product Analyzer

    This application helps you find and compare products available in the Lithuanian market
    based on technical specifications you provide. It leverages the Perplexity API to search
    for and analyze products from various Lithuanian retailers.

    ### How to Use

    1. Enter the technical specifications for the product you're looking for
    2. Click "Search Products"
    3. Review the results, which show:
       - Product details and pricing
       - Technical specifications evaluation
       - Links to product pages

    ### Tips for Best Results

    - Be specific about your requirements
    - Include both must-have and nice-to-have features
    - Specify brand preferences if you have any
    - Include price range if relevant

    ### Technical Details

    This application uses:
    - Streamlit for the web interface
    - Perplexity AI API for intelligent market research
    - JSON for structured data handling

    ### Privacy Note

    Your search queries and technical specifications are sent to the Perplexity API
    to generate results. No personal information is stored or shared beyond what is 
    necessary for the application to function.
    try to present at least 5 products
    """)

# Footer
st.markdown("---")
st.markdown("© 2025 Lithuanian Market Product Analyzer | Powered by Perplexity AI")