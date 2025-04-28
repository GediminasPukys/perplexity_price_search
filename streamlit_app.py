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

    # NEW FEATURE: Search Domains Configuration
    st.subheader("Search Domains Configuration")

    # Default search domains
    default_domains = [
        "vaistai.lt",
        "kainos.lt",
        "kaina24.lt",
        "gintarine.lt",
        "eurovaistine.lt",
        "manovaistine.lt"
    ]

    # Initialize session state for domains if not already set
    if "search_domains" not in st.session_state:
        st.session_state.search_domains = default_domains.copy()

    # Input for adding new domain
    col1, col2 = st.columns([3, 1])
    with col1:
        new_domain = st.text_input("Add new domain (e.g., example.lt):",
                                   placeholder="Enter a Lithuanian domain")
    with col2:
        if st.button("Add Domain") and new_domain:
            if new_domain not in st.session_state.search_domains:
                st.session_state.search_domains.append(new_domain)
                st.success(f"Added {new_domain} to search domains")
            else:
                st.info(f"{new_domain} is already in search domains")

    # Display and manage current domains
    st.write("Current search domains:")
    domains_to_remove = []

    # Display domains in multi-columns for better UI
    domain_cols = st.columns(3)
    for i, domain in enumerate(st.session_state.search_domains):
        col_idx = i % 3
        with domain_cols[col_idx]:
            if st.checkbox(domain, value=True, key=f"domain_{domain}"):
                pass  # Keep domain if checked
            else:
                domains_to_remove.append(domain)

    # Remove unchecked domains
    for domain in domains_to_remove:
        if domain in st.session_state.search_domains:
            st.session_state.search_domains.remove(domain)

    # Reset to defaults button
    if st.button("Reset to Default Domains"):
        st.session_state.search_domains = default_domains.copy()
        st.experimental_rerun()

    # NEW FEATURE: Price Calculation Objective
    st.subheader("Price Calculation Objective")

    price_calculation_options = {
        "none": "No special calculation (standard price)",
        "unit": "Price per unit (e.g., per item)",
        "kg": "Price per kilogram",
        "liter": "Price per liter",
        "package": "Price per package"
    }

    price_calc_objective = st.selectbox(
        "Select how you want prices to be calculated:",
        options=list(price_calculation_options.keys()),
        format_func=lambda x: price_calculation_options[x]
    )

    # Additional input for custom calculation if needed
    custom_calc_unit = None
    if price_calc_objective != "none":
        st.info(f"Products will be evaluated based on {price_calculation_options[price_calc_objective]}")

        if price_calc_objective == "unit":
            custom_calc_unit = st.text_input(
                "Specify unit type (e.g., tablet, pill, piece):",
                placeholder="Leave empty for generic 'unit'"
            )


    # Improved prompt template
    def generate_prompt(tech_spec, price_calc_objective, custom_unit=None):
        # Base prompt
        prompt = f"""Analyze the Lithuanian market and gather detailed product information according to the following technical specification:
{tech_spec}

Follow these guidelines:
1. Tik Lietuviški puslapiai
2. Verify the product is currently available for purchase
3. Gather accurate pricing in EUR
4. Evaluate technical specification requirements one by one
"""

        # Add price calculation objective if selected
        if price_calc_objective != "none":
            if price_calc_objective == "unit":
                unit_type = custom_unit if custom_unit else "unit"
                prompt += f"\n5. Calculate and include price per {unit_type} for each product"
            elif price_calc_objective == "kg":
                prompt += "\n5. Calculate and include price per kilogram for each product"
            elif price_calc_objective == "liter":
                prompt += "\n5. Calculate and include price per liter for each product"
            elif price_calc_objective == "package":
                prompt += "\n5. Calculate and include price per package for each product"

        # JSON format instructions
        prompt += """

Results should be evaluated from all given domains.
IMPORTANT: Your response MUST be formatted EXACTLY as a valid JSON array of product objects.
Each product in the array should have the following fields:

[
  {
    "provider": "Company selling the product",
    "provider_website": "Main website domain (e.g., telia.lt)",
    "provider_url": "Full URL to the specific product page",
    "product_name": "Complete product name with model",
    "product_properties": {
      "key_spec1": "value1",
      "key_spec2": "value2"
    },
    "product_sku": "Any product identifiers (SKU, UPC, model number)",
    "product_price": 299.99,"""

        # Add price calculation field based on objective
        if price_calc_objective != "none":
            if price_calc_objective == "unit":
                unit_type = custom_unit if custom_unit else "unit"
                prompt += f"""
    "price_per_{price_calc_objective}": 9.99,
    "unit_type": "{unit_type}","""
            else:
                prompt += f"""
    "price_per_{price_calc_objective}": 9.99,"""

        # Complete the prompt
        prompt += """
    "evaluation": "Detailed assessment of how the product meets or fails each technical specification"
  }
]

DO NOT include any explanation, preamble, or additional text - ONLY provide the JSON array.
try to present at least 5 products
"""
        return prompt


    # Function to query Perplexity API
    def query_perplexity(prompt, api_key, search_domains):
        url = "https://api.perplexity.ai/chat/completions"
        st.write(search_domains)
        payload = {
            "model": "sonar-pro",
            "search_domain_filter": search_domains,
            "web_search_options": {
                "search_context_size": "high"
            },
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
    def display_results(response_data, price_calc_objective):
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
                "price_calc_objective": price_calc_objective,
                "results": products
            }
            st.session_state.search_history.append(history_entry)

            # Display results in expandable sections
            for i, product in enumerate(products):
                product_title = f"{i + 1}. {product.get('product_name', 'Unknown Product')} - €{product.get('product_price', 'N/A')}"

                # Add price calculation to title if available
                if price_calc_objective != "none":
                    price_per_key = f"price_per_{price_calc_objective}"
                    if price_per_key in product:
                        unit_display = ""
                        if price_calc_objective == "unit" and "unit_type" in product:
                            unit_display = f"/{product['unit_type']}"
                        elif price_calc_objective == "kg":
                            unit_display = "/kg"
                        elif price_calc_objective == "liter":
                            unit_display = "/L"
                        elif price_calc_objective == "package":
                            unit_display = "/pkg"

                        product_title += f" (€{product.get(price_per_key, 'N/A')}{unit_display})"

                with st.expander(product_title):
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.markdown(f"**Provider:** {product.get('provider', 'N/A')}")
                        st.markdown(f"**Website:** {product.get('provider_website', 'N/A')}")
                        if 'provider_url' in product and product['provider_url']:
                            st.markdown(f"**Product Link:** [View Product]({product['provider_url']})")
                        st.markdown(f"**SKU/ID:** {product.get('product_sku', 'N/A')}")
                        st.markdown(f"**Price:** €{product.get('product_price', 'N/A')}")

                        # Display price calculation if available
                        if price_calc_objective != "none":
                            price_per_key = f"price_per_{price_calc_objective}"
                            if price_per_key in product:
                                unit_display = ""
                                if price_calc_objective == "unit" and "unit_type" in product:
                                    unit_display = f"/{product['unit_type']}"
                                elif price_calc_objective == "kg":
                                    unit_display = "/kg"
                                elif price_calc_objective == "liter":
                                    unit_display = "/L"
                                elif price_calc_objective == "package":
                                    unit_display = "/pkg"

                                st.markdown(
                                    f"**Price per {price_calc_objective.capitalize()}:** €{product.get(price_per_key, 'N/A')}{unit_display}")

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
            # Generate prompt with price calculation objective
            prompt = generate_prompt(tech_spec, price_calc_objective, custom_calc_unit)

            # Show prompt in expandable section
            with st.expander("View Search Prompt"):
                st.text(prompt)

            # Get active search domains
            active_domains = [domain for domain in st.session_state.search_domains
                              if st.session_state.get(f"domain_{domain}", True)]

            if not active_domains:
                st.warning("No search domains selected. Using default domains.")
                active_domains = default_domains

            # Query the API with selected domains
            response = query_perplexity(prompt, PERPLEXITY_API_KEY, active_domains)

            # Display results with price calculation info
            display_results(response, price_calc_objective)

with tab2:
    st.header("Search History")

    if "search_history" not in st.session_state or not st.session_state.search_history:
        st.info("No search history yet. Search for products to see your history here.")
    else:
        for i, entry in enumerate(reversed(st.session_state.search_history)):
            # Add price calculation info to history entry title
            price_calc_info = ""
            if "price_calc_objective" in entry and entry["price_calc_objective"] != "none":
                price_calc_info = f" (Price per {entry['price_calc_objective']})"

            with st.expander(f"{entry['timestamp']} - {entry['tech_spec'][:50]}...{price_calc_info}"):
                st.markdown(f"**Search Query:**\n{entry['tech_spec']}")

                # Show price calculation objective if available
                if "price_calc_objective" in entry and entry["price_calc_objective"] != "none":
                    st.markdown(f"**Price Calculation:** Price per {entry['price_calc_objective']}")

                st.markdown(f"**Results:** {len(entry['results'])} products found")

                # Display results again
                for j, product in enumerate(entry['results']):
                    # Basic product info
                    product_info = f"**{j + 1}. {product.get('product_name', 'Unknown Product')}** - €{product.get('product_price', 'N/A')}"

                    # Add price calculation if available
                    if "price_calc_objective" in entry and entry["price_calc_objective"] != "none":
                        price_per_key = f"price_per_{entry['price_calc_objective']}"
                        if price_per_key in product:
                            unit_display = ""
                            if entry["price_calc_objective"] == "unit" and "unit_type" in product:
                                unit_display = f"/{product['unit_type']}"
                            elif entry["price_calc_objective"] == "kg":
                                unit_display = "/kg"
                            elif entry["price_calc_objective"] == "liter":
                                unit_display = "/L"
                            elif entry["price_calc_objective"] == "package":
                                unit_display = "/pkg"

                            product_info += f" (€{product.get(price_per_key, 'N/A')}{unit_display})"

                    st.markdown(product_info)
                    st.markdown(
                        f"Provider: {product.get('provider', 'N/A')} | [View Product]({product.get('provider_url', '#')})")

                # Option to view full details
                if st.button(f"View Full Details #{i}", key=f"history_{i}"):
                    # This recreates the detailed view from the Search tab
                    for j, product in enumerate(entry['results']):
                        # Create product title with price calculation if available
                        product_title = f"{j + 1}. {product.get('product_name', 'Unknown Product')} - €{product.get('product_price', 'N/A')}"

                        if "price_calc_objective" in entry and entry["price_calc_objective"] != "none":
                            price_per_key = f"price_per_{entry['price_calc_objective']}"
                            if price_per_key in product:
                                unit_display = ""
                                if entry["price_calc_objective"] == "unit" and "unit_type" in product:
                                    unit_display = f"/{product['unit_type']}"
                                elif entry["price_calc_objective"] == "kg":
                                    unit_display = "/kg"
                                elif entry["price_calc_objective"] == "liter":
                                    unit_display = "/L"
                                elif entry["price_calc_objective"] == "package":
                                    unit_display = "/pkg"

                                product_title += f" (€{product.get(price_per_key, 'N/A')}{unit_display})"

                        with st.expander(product_title):
                            col1, col2 = st.columns([1, 2])

                            with col1:
                                st.markdown(f"**Provider:** {product.get('provider', 'N/A')}")
                                st.markdown(f"**Website:** {product.get('provider_website', 'N/A')}")
                                if 'provider_url' in product and product['provider_url']:
                                    st.markdown(f"**Product Link:** [View Product]({product['provider_url']})")
                                st.markdown(f"**SKU/ID:** {product.get('product_sku', 'N/A')}")
                                st.markdown(f"**Price:** €{product.get('product_price', 'N/A')}")

                                # Display price calculation if available
                                if "price_calc_objective" in entry and entry["price_calc_objective"] != "none":
                                    price_per_key = f"price_per_{entry['price_calc_objective']}"
                                    if price_per_key in product:
                                        unit_display = ""
                                        if entry["price_calc_objective"] == "unit" and "unit_type" in product:
                                            unit_display = f"/{product['unit_type']}"
                                        elif entry["price_calc_objective"] == "kg":
                                            unit_display = "/kg"
                                        elif entry["price_calc_objective"] == "liter":
                                            unit_display = "/L"
                                        elif entry["price_calc_objective"] == "package":
                                            unit_display = "/pkg"

                                        st.markdown(
                                            f"**Price per {entry['price_calc_objective'].capitalize()}:** €{product.get(price_per_key, 'N/A')}{unit_display}")

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
    2. Configure search domains to include or exclude specific websites
    3. Select a price calculation objective if you want to compare prices on a specific basis
    4. Click "Search Products"
    5. Review the results, which show:
       - Product details and standard pricing
       - Price calculations based on your selected objective (per kg, per unit, etc.)
       - Technical specifications evaluation
       - Links to product pages

    ### Tips for Best Results

    - Be specific about your requirements
    - Include both must-have and nice-to-have features
    - Specify brand preferences if you have any
    - Include price range if relevant
    - Use the price calculation objectives for better comparison between products (e.g., price per kg for groceries)

    ### Technical Details

    This application uses:
    - Streamlit for the web interface
    - Perplexity AI API for intelligent market research
    - JSON for structured data handling
    - Custom domains configuration for targeted searches
    - Specialized price calculations for better product comparison

    ### Privacy Note

    Your search queries and technical specifications are sent to the Perplexity API
    to generate results. No personal information is stored or shared beyond what is 
    necessary for the application to function.
    """)

# Footer
st.markdown("---")
st.markdown("© 2025 Lithuanian Market Product Analyzer | Powered by Perplexity AI")